from ast import Dict
import asyncio
import logging 
import json
import os 
from pathlib import Path
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from enum import Enum
from pydantic import BaseModel
import chardet

ged_level_1_tags = ['BIRT', 'DEAT', 'MARR', 'BURI', 'DIV', 'OCCU', 'RESI', 'CHR']

# Tools schemas 
class ListFiles(BaseModel):
    name: str
    
class RenameFiles(BaseModel):
    file_name: str
    new_name: str
    
class ViewFiles(BaseModel):
    name: str

# Tool names
class AncestryTools(str, Enum):
    LIST_FILES = "list_files"
    RENAME_FILE = "rename_file"
    VIEW_FILES = "view_file"

# Tool helper functions
def find_files_with_name(name: str | None = None, path: Path | None = None) -> list[Path]:
    pattern = f"{name}.ged" if name is not None else "*.ged"
    return list(path.glob(pattern))

def rename_files(new_name: str | None = None, files: list[Path] | None = None) -> tuple[str, list[Dict], str]:
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
        return [], f'An unexpected error ocurred: {str(e)}. Please try again later or contact support.'
    
    return renamed_files, ""

def parse_ged_file(files: list[Path] | None = None) -> tuple[list[Dict], str]:
    try:
        parsed_geds = {}
        for file in files:
            if not file.exists() or file.suffix.lower() != '.ged':
                continue
            
            parsed_geds[file.name] = []
            
            # determine encoding 
            raw_bytes = file.read_bytes()
            result = chardet.detect(raw_bytes)
            # open file, and parse ged data
            try:
                with file.open(encoding=result['encoding']) as ged:
                    ged_obj = {}
                    cur_lvl1_tag = None
                    
                    for line in ged:
                        '''
                        Level 0: root records
                        Level 1: main info about records
                        Level 2: details about level 1 info
                        '''
                        parts = line.strip().split(' ', 2)
                        if not parts: 
                            continue
                        level = int(parts[0])
                        tag = parts[1]
                        value = parts[2] if len(parts) > 2 else ''

                        if level == 0: 
                            # save prev obj if exists
                            if ged_obj and 'type' in ged_obj:
                                parsed_geds[file.name].append(ged_obj)
                                
                            ged_obj = {}
                            if '@' in tag: # ID
                                ged_obj['id'] = tag
                                ged_obj['type'] = value
                        elif level == 1:
                            cur_lvl1_tag = tag
                            if tag in ged_level_1_tags:
                                ged_obj[tag] = {}
                            else:
                                ged_obj[tag] = value
                        elif level == 2 and cur_lvl1_tag:
                            # If parent is an event
                            if cur_lvl1_tag in ged_level_1_tags:
                                if cur_lvl1_tag not in ged_obj:
                                    ged_obj[cur_lvl1_tag] = {}
                                ged_obj[cur_lvl1_tag][tag] = value
                            elif cur_lvl1_tag == 'NAME':
                                ged_obj[f'NAME_{tag}'] = value
                            else:
                                ged_obj[tag] = value
                                
                    if ged_obj and 'type' in ged_obj:
                        parsed_geds[file.name].append(ged_obj)
            except UnicodeDecodeError:
                return [], f'File could not be decoded, please check encoding on the .ged'
    except Exception as e:
        return [], f'An unexpected error occured: {str(e)}. Please try again later or contact support.'
    return parsed_geds, ""

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
            ),
            types.Tool(
                name=AncestryTools.VIEW_FILES,
                description="View a GEDCOM file in plaintext format",
                inputSchema=ViewFiles.model_json_schema()
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
            case AncestryTools.VIEW_FILES:
                # get files, if none found tell serve rthat
                gedcom_files = find_files_with_name(arguments["name"].removesuffix('.ged'), path)
                if not gedcom_files:
                    return [
                        types.TextContent(
                            type="text",
                            text=f'No files found matching {arguments["name"]}'
                        )    
                    ]
                
                # show file, if error message tell server
                parsed_geds, message = parse_ged_file(gedcom_files)
                
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
                        text=json.dumps({filename: data}, indent=2)
                    )
                    for filename, data in parsed_geds.items()
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