# Ancestry MCP Server
[![MIT licensed][mit-badge]][mit-url]
[![Python Version][python-badge]][python-url]

[mit-badge]: https://img.shields.io/pypi/l/mcp.svg
[mit-url]: https://github.com/reeeeemo/ancestry-mcp/blob/main/LICENSE
[python-badge]: https://img.shields.io/pypi/pyversions/mcp.svg
[python-url]: https://www.python.org/downloads/

Built on top of the [Model Context Protocol Python SDK](https://modelcontextprotocol.io)

## Overview

Python server implementing Model Context Protocol (MCP) for interactibility with `.ged` files *(Ancestry files)*

## Features
    
- Read and parse .ged files
- Rename `.ged` files
- Search within .ged files for certain individuals, family, etc

**Note:** The server will only allow operations within the directory specified via `args`

## Resources

- `gedcom://{file_name}`: `.ged` operations interface

## Tools

- **list_files**
    - List a (or multiple) `.ged` file within the directory
    - Input: `name` (string)

- **rename_file**
    - Renames a (or multiple) `.ged` file within the directory
    - Inputs:
        - `file_name` (string): Old file name
        - `new_name` (string)
 
- **view_file**
    - Parses and reads full contents of a `.ged` file
    - Can also parse and read multiple files
    - Can get specific information out of file(s), such as date of birth, marriage, etc.
    - Input: `name` (string)


## Usage with Claude Desktop
Add this to your `claude_desktop_config.json` (will be updated to pypi soon):

```json
{
  "mcpServers": {
     "ancestry": {
       "command": "mcp-server-ancestry",
       "args": ["--gedcom-path", "path/to/your/gedcom/files"],
       "cwd": "path/to/work/directory"
     }
  }
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
