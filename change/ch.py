import requests
import json
import os
import time
import sys
from urllib3.exceptions import InsecureRequestWarning
import urllib3

urllib3.disable_warnings(InsecureRequestWarning)

input_data_string = os.getenv("INPUT_DATA")
try:
    input_data = json.loads(input_data_string)
except json.JSONDecodeError:
    input_data = {
        "change_id": "",
        "change_action": "",
        "close_details_id": ""
    }

script_output_data_string = os.getenv("SCRIPT_OUTPUT_DATA")
try:
    script_output_data = json.loads(script_output_data_string)
except json.JSONDecodeError:
    script_output_data = {
        "status": "",
        "comment": "",
        "applied_files": [],
        "not_applied_files": []
    }

chr_action = os.getenv("CHR_ACTION") # REQUIRED
if chr_action.lower() not in ["create", "view", "update", "close", "delete"]:
    raise ValueError(f"Invalid change action: {chr_action}")

script_status_success = script_output_data.get("status", "false")
script_status_comment = script_output_data.get("comment", "Критические ошибки при выполнении скрипта")
script_status_log = f"Применены скрипты:\n{script_output_data.get("applied_files", "")}\nПропущенные скрипты:\n{script_output_data.get("not_applied_files", "")}"
close_details_id = input_data.get("close_details_id", "")

url = f"{os.getenv("HD_API_URL")}/changes"
api_token = os.getenv("HD_API_TOKEN")
headers = {"authtoken": api_token}
unix_start_time_ms = int(time.time() * 1000) # in milliseconds
planned_solve_time = os.getenv("PLANNED_SOLVE_TIME") # in minutes
unix_end_time_ms = unix_start_time_ms + (int(planned_solve_time) * 60 * 1000) # in milliseconds

template_id = os.getenv("TEMPLATE_ID") # Standard Change
services_id = os.getenv("SERVICES_ID") # Other

commit_url = os.getenv("COMMIT_URL")
service_name = os.getenv("SERVICE_NAME")
approvers_list = os.getenv("APPROVERS_LIST")
description = os.getenv("DESCRIPTION")
if not description:
    description = f"<div>Применение скриптов Pull Request {commit_url} по базе данных сервиса {service_name}, reviewers: {approvers_list}</div>"  # hardcode description
title = os.getenv("TITLE")
if not title:
    title = f"Автоматическое применение скриптов по согласованию Pull Request"

def get_user_id(user_email):
    url = f"{os.getenv('HD_API_URL')}/users"
    input_data = {
        "list_info": {
            "sort_field": "name",
            "start_index": 1,
            "sort_order": "asc",
            "row_count": "25",
            "get_total_count": "true",
            "search_fields": {
                "email_id": user_email
            }
        },
        "fields_required": []
    }
    params = {'input_data': json.dumps(input_data)}
    response = requests.get(url,headers=headers,params=params,verify=False)
    users = response.json().get("users", [])
    if not users or not users[0].get("id"):
        print(f"\033[91m[ERROR]\033[0m Пользователь с email {user_email} не найден или у него нет ID")
        sys.exit(1)
    return users[0]["id"]

change_type_id = os.getenv("CHANGE_TYPE_ID") # Standard
change_manager_id = get_user_id(os.getenv("CHANGE_MANAGER_EMAIL")) # REQUIRED
change_owner_id = get_user_id(os.getenv("CHANGE_OWNER_EMAIL")) # REQUIRED
try:
    change_requester_id = get_user_id(os.getenv("CHANGE_REQUESTER_EMAIL"))
except Exception as e:
    print(f"\033[93m[WARNING]\033[0m: Пользователь, создавший PR, не найден в helpdesk. Автор изменения будет установлен как запросивший изменение")
    print(f"\033[93m[WARNING]\033[0m: Дополнительная информация по ошибке {e}")
    change_requester_id = change_owner_id

workflow_id = os.getenv("WORKFLOW_ID") # Standard Change
reason_for_change_id = os.getenv("REASON_FOR_CHANGE_ID") # Maintenance

change_data = {
    "change": {
        "template": {
            "id": template_id
        },
        # "next_review_on": {
        #     "value": "1671392007925"
        # },
        # "category": {
        #     "id": "3"
        # },
        "services": [
            {
                "id": services_id
            }
        ],
        # "subcategory": {
        #     "id": "8"
        # },
        # "item": {
        #     "id": "8"
        # },
        "description": description,
        "title": title,
        "change_type": {
            "id": change_type_id
        },
        "change_manager": {
            "id": change_manager_id
        },
        "change_owner": {
            "id": change_owner_id
        },
        # "priority": {
        #     "id": "4"
        # },
        "scheduled_end_time": {
            "value": unix_end_time_ms
        },
        # "impact": {
        #     "id": "3"
        # },
        # "urgency": {
        #     "id": "3"
        # },
        # "risk": {
        #     "id": "3"
        # },
        "scheduled_start_time": {
            "value": unix_start_time_ms
        },
        "assets": [],
        "change_requester": {
            "id": change_requester_id
        },
        "workflow": {
            "id": workflow_id
        },
        "reason_for_change": {
            "id": reason_for_change_id
        },
        # "roles": [
        #     {
        #         "role": {
        #             "id": "8"
        #         },
        #         "user": {
        #             "id": "5"
        #         }
        #     },
        #     {
        #         "role": {
        #             "id": "8"
        #         },
        #         "user": {
        #             "id": "7"
        #         }
        #     }
        # ],
        "close_details": {
            "description": f"{script_status_log}",
            "id": f"{close_details_id}"
        },
        # "stage": {
        #     "id": "4"
        # },
        # "status": {
        #     "id": "3"
        # }
    }
}

data = {'input_data': json.dumps(change_data)}

match chr_action.lower():
  case "create":
    response = requests.post(url,headers=headers,data=data,verify=False)
    with open('response_create.json', 'w', encoding='utf-8') as f:
        json.dump(response.json(), f, indent=4, ensure_ascii=False)
  case "view":
    change_id = input_data.get("change_id", "")
    url = f"{os.getenv('HD_API_URL')}/changes/{change_id}"
    response = requests.get(url,headers=headers,verify=False)
    with open('response_view.json', 'w', encoding='utf-8') as f:
        json.dump(response.json(), f, indent=4, ensure_ascii=False)
  case "update":
    change_id = input_data.get("change_id", "")
    url = f"{os.getenv('HD_API_URL')}/changes/{change_id}"
    response = requests.put(url,headers=headers,data=data,verify=False)
    with open('response_update.json', 'w', encoding='utf-8') as f:
        json.dump(response.json(), f, indent=4, ensure_ascii=False)
  case "delete":
    change_id = input_data.get("change_id", "")
    url = f"{os.getenv('HD_API_URL')}/changes/{change_id}"
    response = requests.delete(url,headers=headers,verify=False)
    with open('response_delete.json', 'w', encoding='utf-8') as f:
        json.dump(response.json(), f, indent=4, ensure_ascii=False)
  case "close":
    change_id = input_data.get("change_id", "")
    ### may be need in next ME version
    # input_data_close = {
    #         "status": {
    #             "name": "Completed",
    #             "id": "12"
    #         },
    #         "comment": "some comment",
    #         "close_details": {
    #             "description": "some description"
    #         },
    #         # "closure_code": {
    #         #     "name": "Closed - Completed"
    #         # },
    #         # "attachments": [
    #         #     {
    #         #         "id": "2"
    #         #     }
    #         # ]
    # }

    input_data_close = {
        "comment": f"{script_status_comment}",
        "status": f"{'completed' if script_status_success == 'true' else 'canceled'}",
    }

    data_close = {'input_data': json.dumps(input_data_close)}
    url = f"{os.getenv('HD_API_URL')}/changes/{change_id}/close_change"
    response = requests.put(url,headers=headers,data=data_close,verify=False)
    with open('response_close.json', 'w', encoding='utf-8') as f:
        json.dump(response.json(), f, indent=4, ensure_ascii=False)
if response.json()["response_status"]["status_code"] != 2000:
    print(f"\033[91m[ERROR]\033[0m: {response.text}")
    sys.exit(1)
else:
    output_data = {
        "change_id": response.json()["change"]["id"],
        "change_action": chr_action.lower(),
        "close_details_id": response.json()["change"]["close_details"]["id"]
    }
with open("output.json", "w") as json_file:
    json.dump(output_data, json_file)