# qbj_parser
Python script that converts neg5 QBJ files to sqbs files.  
Note: If a team has quote characters in its name ("Team Name"), the quotes must be escaped in the settings json file like so:
```
{
    "name": "example pool",
    "teams": [
        "\"Team Name\""
    ]
}
```
