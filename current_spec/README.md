# Current A2A Specifications

This directory contains the current baseline A2A specifications used for change tracking and test impact analysis.

## Files

- `A2A_SPECIFICATION.md` - Current A2A protocol specification (Markdown)
- `a2a_schema.json` - Current A2A JSON schema definition
- `version_info.json` - Version tracking metadata

## Workflow

### 1. Initial Setup
The specifications in this directory serve as the baseline for comparison with the latest versions from GitHub.

### 2. Running Spec Analysis
To check for changes and analyze test impacts:
```bash
cd spec_tracker
python main.py
```

This will:
- Download the latest specs from GitHub
- Compare them with the current specs in this directory
- Generate a change analysis report
- Identify affected tests

### 3. Updating Current Specs
After reviewing the analysis report and fixing any issues in your tests, update the baseline specifications:

```bash
# Update to latest version from GitHub
python update_current_spec.py --version "v1.2.0"

# Dry run to see what would change
python update_current_spec.py --dry-run

# Force update even if no changes detected
python update_current_spec.py --force --version "v1.2.0"
```

### 4. Version Bumping Process

1. **Run spec analysis**: `python spec_tracker/main.py`
2. **Review the analysis report** to understand changes and test impacts
3. **Fix any test issues** identified in the report
4. **Update baseline specs**: `python update_current_spec.py --version "v1.3.0"`
5. **Commit the updated baseline** with the new version tag

## Version Info

The `version_info.json` file tracks:
- `updated_at`: Timestamp of last update
- `old_version`: Previous version identifier
- `new_version`: Current version identifier  
- `source`: Source of the specifications

## Backup

When updating specifications, the previous versions are automatically backed up to `current_spec_backup/` directory.

## Commands Reference

### Update Script Options
```bash
python update_current_spec.py --help
```

Key options:
- `--version "v1.2.0"`: Tag the update with a version
- `--dry-run`: Preview changes without updating
- `--force`: Update even if no changes detected
- `--verbose`: Enable detailed logging
- `--backup-dir path`: Custom backup location

### Spec Tracker Options
```bash
python spec_tracker/main.py --help
```

Key options:
- `--output report.md`: Custom report output file
- `--summary-only`: Generate concise summary only
- `--json-export data.json`: Export analysis as JSON 