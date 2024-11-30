import asyncio
import logging 
import os 
from pathlib import Path
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from enum import Enum
from pydantic import BaseModel

# Tools schemas 
class ListFiles(BaseModel):
    name: str
    
class RenameFiles(BaseModel):
    file_name: str
    new_name: str

# Tool names
class AncestryTools(str, Enum):
    LIST_FILES = "list_files"
    RENAME_FILE = "rename_file"

# Tool helper functions
def find_files_with_name(name: str | None = None, path: Path | None = None) -> list[Path]:
    pattern = f"{name}.ged" if name is not None else "*.ged"
    return list(path.glob(pattern))

def rename_files(new_name: str | None = None, files: list[Path] | None = None) -> tuple[list[Path], str]:
    try:
        renamed_files = []
        for file in files:
            try:
                new_path = file.parent / f"{new_name.removesuffix('.ged')}.ged"
                if new_path.exists():
                    return [], f"Cannot rename, {new_path.name} already exists"
                file.rename(new_path)
                renamed_files.append(new_path)
            except PermissionError:
                return [], f'Permission denied: Cannot rename {file.name}. Check write perms'
            except OSError as e:
                return [], f'Error renaming {file.name}: {str(e)}'
    except Exception as e:
        return [], f'An unexpected error ocurred: {str(e)}, Please try again later or contact support.'
    
    return renamed_files, ""

# logging config
logging.basicConfig(
    filename='mcp_ancestry.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
    
    )

# server main code
async def serve(gedcom_path: str | None = None) -> None:
    app = Server("ancestry")
    
    # Verification of GEDCOM path
    path = Path(gedcom_path)
    if not path.exists():
        raise ValueError(f'Invalid path: {gedcom_path}')
    if not path.is_dir():
        raise ValueError(f'GEDCOM path is not a directory: {gedcom_path}')

    if not os.access(path, os.R_OK):
        raise ValueError(f'GEDCOM path does not have read / write permissions: {gedcom_path}')
    
    # debug stuff ! 
    logging.debug(f'Path exists and is valid: {path.absolute()}')
    logging.debug(f'Contents of directory: {list(path.iterdir())}')

    # makes GEDCOM files visible to Claude
    @app.list_resources()
    async def list_resources() -> list[types.Resource]:
        gedcom_files = list(path.glob("*.ged"))
        # scan gedcom path dir for .ged files
        return [
            types.Resource(
                uri=f"gedcom://{file.name}",
                name=file.name,
                mimeType="application/x-gedcom"
            )
            for file in gedcom_files
        ]
    

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=AncestryTools.LIST_FILES,
                description="List GEDCOM files",
                inputSchema=ListFiles.model_json_schema()
            ),
            types.Tool(
                name=AncestryTools.RENAME_FILE,
                description="Rename a GEDCOM file",
                inputSchema=RenameFiles.model_json_schema()
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, 
    arguments: dict) -> list[types.TextContent]:
        match name:
            case AncestryTools.LIST_FILES:
                gedcom_files = find_files_with_name(arguments["name"].removesuffix('.ged'), path)
                return [
                    types.TextContent(
                        type="text",
                        text=f"File: {file.name}\nSize: {file.stat().st_size} bytes\nURI: gedcom://{file.name}"
                    )
                    for file in gedcom_files
                ]
            case AncestryTools.RENAME_FILE:
                # get files, if none found tell server that
                gedcom_files = find_files_with_name(arguments["file_name"].removesuffix('.ged'), path)
                if not gedcom_files:
                    return [
                        types.TextContent(
                            type="text",
                            text=f'No files found matching {arguments["file_name"]}'
                        )    
                    ]
                # rename files, if error message tell server
                renamed_files, message = rename_files(arguments["new_name"].removesuffix('.ged'), gedcom_files)
                if message:
                    return [
                        types.TextContent(
                            type="text",
                            text=message
                        )
                    ]
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"{file.name}\nURI:gedcom://{file.name}"
                    )
                    for file in renamed_files
                ]
            case _:
                raise ValueError(f"Unknown Tool: {name}")
        
    
    async with stdio_server() as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(serve())