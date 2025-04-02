#!/usr/bin/env python3
"""
Project configuration validator implementation.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set, Tuple

from .schema_validator import JsonSchemaValidator

logger = logging.getLogger("json_schema")


class ConfigValidator:
    """Validates project configuration files against a schema with custom rules."""

    def __init__(
        self,
        check_file_existence: bool = False,
        verbose: bool = False,
        base_dir: Optional[Path] = None,
        cmake_vars: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the configuration validator.

        Args:
            check_file_existence: If True, verify that referenced files exist on disk
            verbose: If True, log additional details during validation
            base_dir: Base directory for resolving relative file paths
            cmake_vars: Dictionary of CMake variables for expanding in prefixes
        """
        self.check_file_existence = check_file_existence
        self.base_dir = base_dir or Path.cwd()
        self.verbose = verbose
        self.schema_validator = JsonSchemaValidator(verbose=verbose)
        self.cmake_vars = cmake_vars or {}

        # Default CMake variables
        if "CMAKE_CURRENT_LIST_DIR" not in self.cmake_vars:
            self.cmake_vars["CMAKE_CURRENT_LIST_DIR"] = str(self.base_dir)

        if verbose:
            logger.setLevel(logging.DEBUG)

    def load_json(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        Load and parse a JSON file.

        Args:
            filepath: Path to the JSON file

        Returns:
            Parsed JSON data as a dictionary

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Enhance the error message with file information
            raise json.JSONDecodeError(
                f"Failed to parse JSON in {filepath}: {e.msg}",
                e.doc,
                e.pos
            ) from e

    def _expand_cmake_vars(self, path_str: str) -> str:
        """
        Expand CMake variables in a path string.

        Args:
            path_str: Path string potentially containing CMake variables like ${VAR}

        Returns:
            Expanded path string
        """
        # Simple CMake variable expansion
        result = path_str
        for var_name, var_value in self.cmake_vars.items():
            result = result.replace(f"${{{var_name}}}", var_value)

        return result

    def _get_file_prefix(self, project_config: Dict[str, Any], section: str) -> Path:
        """
        Get the appropriate prefix path for a file section.

        Args:
            project_config: Project configuration data
            section: File section name (e.g., 'includes', 'sources')

        Returns:
            Path object for the prefix
        """
        # Determine which prefix to use based on section
        if section in ["includes", "module_includes"]:
            prefix_key = "include_prefix"
            default_prefix = "${CMAKE_CURRENT_LIST_DIR}/include"
        elif section in ["sources", "module_sources"]:
            prefix_key = "source_prefix"
            default_prefix = "${CMAKE_CURRENT_LIST_DIR}/src"
        else:
            # For unknown sections, use base directory
            return self.base_dir

        # Get prefix from project config or use default
        prefix_str = project_config.get(prefix_key, default_prefix)

        # Expand CMake variables
        expanded_prefix = self._expand_cmake_vars(prefix_str)

        # Convert to Path
        prefix_path = Path(expanded_prefix)

        # If relative, make it relative to base_dir
        if not prefix_path.is_absolute():
            prefix_path = self.base_dir / prefix_path

        return prefix_path

    def _validate_project(self, project_path: str, project_config: Dict[str, Any]) -> List[str]:
        """
        Validate a single project configuration.

        Args:
            project_path: Path to the project in the configuration
            project_config: Project configuration data

        Returns:
            List of validation errors for this project
        """
        errors = []

        # Type validations for critical fields
        for field in ["library", "executable", "install"]:
            if field in project_config and not isinstance(project_config[field], bool):
                errors.append(
                    f"Project '{project_path}': '{field}' must be a boolean, not {type(project_config[field]).__name__}"
                )

        # Validate path prefixes if they exist
        for prefix_key in ["include_prefix", "source_prefix"]:
            if prefix_key in project_config:
                prefix_value = project_config[prefix_key]
                if not isinstance(prefix_value, str):
                    errors.append(
                        f"Project '{project_path}': '{prefix_key}' must be a string, not {type(prefix_value).__name__}"
                    )
                elif self.check_file_existence:
                    # Try to expand and resolve the prefix
                    try:
                        expanded_prefix = self._expand_cmake_vars(
                            prefix_value)
                        prefix_path = Path(expanded_prefix)
                        if not prefix_path.is_absolute():
                            prefix_path = self.base_dir / prefix_path

                        # Warn if the directory doesn't exist
                        if not prefix_path.exists():
                            logger.warning(
                                f"Warning: Directory for '{prefix_key}' doesn't exist: {prefix_path}")
                        elif not prefix_path.is_dir():
                            errors.append(
                                f"Project '{project_path}': '{prefix_key}' is not a directory: {prefix_path}"
                            )
                    except Exception as e:
                        errors.append(
                            f"Project '{project_path}': Failed to resolve '{prefix_key}': {str(e)}"
                        )

        # Check file sections
        file_sections = ["includes", "module_includes",
                         "sources", "module_sources"]
        for section in file_sections:
            if section in project_config and isinstance(project_config[section], list):
                errors.extend(self._validate_file_section(
                    project_path, section, project_config[section], project_config))

        return errors

    def _validate_file_section(self, project_path: str, section: str, groups: List[Dict[str, Any]],
                               project_config: Dict[str, Any]) -> List[str]:
        """
        Validate a file section in the project.

        Args:
            project_path: Path to the project
            section: Section name (includes, sources, etc.)
            groups: List of file groups
            project_config: Full project configuration

        Returns:
            List of validation errors
        """
        errors = []
        file_paths: Set[str] = set()
        valid_platforms = ["any", "windows", "apple", "linux", "posix"]

        for i, group in enumerate(groups):
            group_path = f"{project_path}/{section}[{i}]"

            # Check platform field
            if "platform" not in group:
                errors.append(
                    f"Error at '{group_path}': Missing 'platform' field")
            elif group["platform"] not in valid_platforms:
                errors.append(
                    f"Error at '{group_path}': Invalid platform '{group['platform']}', " +
                    f"must be one of: {', '.join(valid_platforms)}"
                )

            # Check for at least one visibility section (public/private)
            has_visibility = False
            for visibility in ["public", "private"]:
                if visibility in group:
                    has_visibility = True

                    if not isinstance(group[visibility], list):
                        errors.append(
                            f"Error at '{group_path}/{visibility}': Must be an array")
                        continue

                    # Check file paths
                    for file_path in group[visibility]:
                        if not isinstance(file_path, str):
                            errors.append(
                                f"Error at '{group_path}/{visibility}': File path must be a string, " +
                                f"not {type(file_path).__name__}"
                            )
                            continue

                        # Check for duplicate file paths
                        if file_path in file_paths:
                            errors.append(
                                f"Duplicate file path at '{group_path}/{visibility}': {file_path}")
                        file_paths.add(file_path)

                        # Verify file existence if requested
                        if self.check_file_existence:
                            # Get appropriate prefix for this section
                            prefix_path = self._get_file_prefix(
                                project_config, section)

                            # Construct full path with prefix
                            full_path = prefix_path / file_path

                            if full_path.exists():
                                logger.debug(f"found: '{group_path}/{visibility}': {file_path}")
                            else:
                                errors.append(
                                    f"File not found: '{full_path}' referenced in '{group_path}/{visibility}'"
                                )

            if not has_visibility:
                errors.append(
                    f"Error at '{group_path}': Must have either 'public' or 'private' section")

        return errors

    def _perform_custom_validations(self, data: Dict[str, Any]) -> List[str]:
        """
        Perform custom validations not covered by the schema.

        Args:
            data: The project configuration data

        Returns:
            List of validation errors
        """
        errors = []

        # Validate each project
        for project_name, project_config in data.items():
            if not isinstance(project_config, dict):
                errors.append(
                    f"Project '{project_name}' has invalid configuration (not an object)")
                continue

            # Validate this project's configuration
            project_errors = self._validate_project(
                project_name, project_config)
            errors.extend(project_errors)

        return errors

    def validate(self, data_file: Union[str, Path], schema_file: Union[str, Path]) -> List[str]:
        """
        Validate a JSON configuration file against a schema.

        Args:
            data_file: Path to the data file to validate
            schema_file: Path to the schema file

        Returns:
            List of validation errors
        """
        errors = []

        # Load JSON files
        try:
            data = self.load_json(data_file)
        except FileNotFoundError as e:
            return [f"File not found: {e}"]
        except json.JSONDecodeError as e:
            return [str(e)]

        try:
            schema = self.load_json(schema_file)
        except FileNotFoundError as e:
            return [f"Schema file not found: {e}"]
        except json.JSONDecodeError as e:
            return [f"Invalid schema JSON: {e}"]

        # Perform schema validation
        schema_errors = self.schema_validator.validate(data, schema)
        errors.extend(schema_errors)

        # Only perform custom validations if schema validation passed
        if not schema_errors:
            custom_errors = self._perform_custom_validations(data)
            errors.extend(custom_errors)

        return errors
