function(task, responses){
    function getOutcomeColour(text){
        switch (text) {
            case "High":
                return {"backgroundColor": "rgb(251, 139, 138)"}
            case "Med":
                return {"backgroundColor": "rgb(242, 183, 145)"}
            case "Low":
                return {"backgroundColor": "rgb(177, 213, 154)"}
            default:
                return {}
        }
    }

    if(task.status.includes("error")){
        const combined = responses.reduce( (prev, cur) => {
            return prev + cur;
        }, "");
        return {'plaintext': combined};
    }else if(task.completed){
        if(responses.length > 0){
            try{
                let data = JSON.parse(responses[0]);
                let output_table = [];
                for(let i = 0; i < data.length; i++){
                    let outcomeText = "";
                    let cellStyle = {};
                    if(data[i]["outcome"]["path"] == "TBD"){
                        outcomeText = "TBD";
                    } else if (data[i]["outcome"]['path'].startsWith("Alerted")) {
                        outcomeText = `Alerted (${data[i]["outcome"]['abbreviation']})`;
                        cellStyle = getOutcomeColour(data[i]["outcome"]['abbreviation']);
                    } else if (data[i]["outcome"]['path'].startsWith("Blocked")) {
                        outcomeText = `Blocked (${data[i]["outcome"]['abbreviation']})`;
                        cellStyle = getOutcomeColour("High");
                    } else {
                        outcomeText = ""
                        cellStyle = {}
                    }
                    let execution_time = ""
                    if (data[i]["attackStart"] != null) {
                        execution_time = new Date(data[i]["attackStart"]["createTime"]).toString()
                    }

                    let execution_artifact_count = "0"
                    if (data[i]["executionArtifactIdInfo"] != null) {
                        execution_artifact_count = data[i]["executionArtifactIdInfo"].length.toString()
                    }

                    output_table.push({
                        "id": {"plaintext": data[i]["id"], "copyIcon": true },
                        "timestamp": {"plaintext": execution_time},
                        "name": {"plaintext": data[i]["name"]},
                        "method": {"plaintext":  data[i]["method"]},
                        "mitreId": {"plaintext":  data[i]["mitreId"]},
                        "EA": {"plaintext":  execution_artifact_count, "startIcon": "upload", "startIconHoverText":"Execution Artifacts"},
                        "tags": {
                            "plaintext": data[i]["tags"].map(tag => tag.name).join(", ")
                        },
                        "status": {"plaintext":  data[i]["status"]},
                        "outcome": {"plaintext":  outcomeText, "cellStyle": cellStyle},
                        "description": {
                            "button": {
                                "name": "Expand",
                                "type": "string",
                                "value": data[i]["description"],
                                "title": "description",
                                "hoverText": "View full description"
                            }
                        },
                        "outcomeNotes": {
                            "button": {
                                "name": "Expand",
                                "type": "string",
                                "value": data[i]["outcomeNotes"],
                                "title": "description",
                                "hoverText": "View outcome notes"
                            }
                        },
                        "actions": {
                            "button": {
                                "name": "Actions",
                                "type": "menu",
                                "value": [
                                    {
                                        "name": "Delete Test Case",
                                        "type": "task",
                                        "ui_feature": "vectr:testcase_delete",
                                        "parameters": data[i]["id"]
                                    }
                                ]
                            }
                        },
                    });
                }
                return {
                    "table": [
                        {
                            "headers": [
                                {"plaintext": "id", "type": "string", "width": 100},
                                {"plaintext": "timestamp", "type": "string", "width": 285},
                                {"plaintext": "name", "type": "string", "fillWidth": true},
                                {"plaintext": "method", "type": "string", "fillWidth": true},
                                {"plaintext": "mitreId", "type": "string", "width": 100},
                                {"plaintext": "EA", "type": "string", "width": 50},
                                {"plaintext": "tags", "type": "string", "fillWidth": true},
                                {"plaintext": "status", "type": "string", "width": 125},
                                {"plaintext": "outcome", "type": "string", "width": 200},
                                {"plaintext": "description", "type": "button", "cellStyle": {}, "width": 150, "disableSort": true},
                                {"plaintext": "outcomeNotes", "type": "button", "cellStyle": {}, "width": 150, "disableSort": true},
                                {"plaintext": "actions", "type": "button", "width": 90, "disableSort": true}
                            ],
                            "rows": output_table,
                            "title": "Test Cases"
                        }
                    ]
                }
            }catch(error){
                console.log(error);
                const combined = responses.reduce( (prev, cur) => {
                    return prev + cur;
                }, "");
                return {'plaintext': combined};
            }
        }else{
            return {"plaintext": "No output from command"};
        }
    }else{
        return {"plaintext": "No data to display..."};
    }
}