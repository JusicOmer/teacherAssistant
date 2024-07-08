import json
import time
import openai
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from excelmain import save_drive_files
from apihandle import list_unread_emails, get_attachments_from_email, send_email_with_attachment, list_files, \
    delete_file, download_file_from_drive, authenticate_gmail
from email_sender import create_message, send_message
from sheethandle import mark_homework_done
from sheetmain import read_sheet, write_sheet, append_sheet

openai.api_key = 'sk-proj-rAfqeibR4AdcLXdggIiXT3BlbkFJeL0YJ10kdiJwRG8msvm7'

app = FastAPI()

user_message = ''


class ChatRequest(BaseModel):
    text: str


@app.post("/chat")
async def chat(request: ChatRequest):
    await save_drive_files()
    global user_message
    user_message = request.text

    # OpenAI Assistant Setup
    assistant_id = 'asst_wWASMpy77WLNZJRPmWsAGRHs'
    thread = openai.beta.threads.create()

    message = openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    while run.status not in ['completed', 'failed']:
        await asyncio.sleep(1)
        run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == 'requires_action':
            run = await submit_tool_outputs(thread.id, run.id, run.required_action.submit_tool_outputs.tool_calls)

    messages = openai.beta.threads.messages.list(thread_id=thread.id)

    response_texts = []
    for msg in messages.data:
        for content in msg.content:
            if content.type == 'text':
                response_texts.append(content.text.value)

    return response_texts[0].replace("\n", " ")


async def list_drive_files():
    files = await find_file(user_message)
    if files:
        return {"files": files}
    else:
        raise HTTPException(status_code=500, detail="Could not retrieve files")


async def list_all_files():
    return list_files()


async def delete_file_by_name():
    file = await find_file(user_message)
    print(type(file))
    print(file)
    if file:
        return delete_file(file)
    else:
        raise HTTPException(status_code=500, detail="Could not retrieve files")


async def list_unread_emails_endpoint():
    emails = list_unread_emails()
    if emails:
        return {"emails": emails}
    else:
        raise HTTPException(status_code=500, detail="Could not retrieve unread emails")


@app.get("/get_attachments/{email_id}/{store_dir}")
async def get_attachments_endpoint(email_id: str, store_dir: str):
    result = get_attachments_from_email(email_id, store_dir)
    if result:
        return {"message": result}
    else:
        raise HTTPException(status_code=500, detail="Could not retrieve attachments")


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    message_text: str
    fileid: str


async def mark_homework_done1(student_name):
    return mark_homework_done(student_name)


import asyncio


async def submit_tool_outputs(thread_id, run_id, tools_to_call):
    tool_output_array = []
    function_lookup = {
        "list_drive_files": list_drive_files,
        "list_all_files": list_all_files,  # vortragen
        "delete_drive_file": delete_file_by_name,  # vortragen
        "list_unread_emails": list_unread_emails_endpoint,  # vortragen
        "read_sheet": read_sheet,
        "write_sheet": write_sheet,
        "append_sheet": append_sheet,
        "mark_homework_done1": mark_homework_done,
        "send_email_to_all_students": email_students  # vortragen
    }

    for tool in tools_to_call:
        tool_call_id = tool.id
        function_name = tool.function.name
        function_args = json.loads(tool.function.arguments)

        function_to_call = function_lookup.get(function_name)
        if function_to_call:
            output = await function_to_call(**function_args)  # Make sure function_to_call is async
            if output:
                tool_output_array.append({"tool_call_id": tool_call_id, "output": json.dumps(output)})
            else:
                tool_output_array.append({"tool_call_id": tool_call_id, "output": "Failed to execute function."})
        else:
            tool_output_array.append({"tool_call_id": tool_call_id, "output": "Function not found."})

    return openai.beta.threads.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run_id,
        tool_outputs=tool_output_array
    )


def get_file_data(excel_path="google_drive_files.xlsx"):
    try:
        df = pd.read_excel(excel_path)
        files = [{"name": row["Name"], "id": row["ID"]} for index, row in df.iterrows()]
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading Excel file: {str(e)}")


# Endpoint to process natural language queries
async def find_file(strChat):
    files = get_file_data()
    query = strChat

    # Generate the prompt for the OpenAI API
    file_list_str = "\n".join([f"Name: {file['name']}, ID: {file['id']}" for file in files])
    prompt = (
        f"You have the following files:\n{file_list_str}\n\n"
        f"Find the files with their names and ids that best match the following query: '{query}'. "
        f"If there is more than one with the same or similar name, give them all in a JSON array exactly like this 'file_name': 'Ron.jpg', 'file_id': '18FO9xKhRmUOEKTW1f6mi2v61VK216gAr'."
    )
    print(prompt)

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant designed to fined out of all the given file names the right ones and to output JSON with the keys file_name and file_id."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        print(response)
        json_response = json.loads(response.choices[0].message.content)
        print(json_response)
        file_ids = json_response['file_id']
        print('file ids')
        print(file_ids)
        return file_ids
        #print(json_response)
        #return json_response['file_id']
        #matched_file = json_response['file_id']
        #return matched_file
    except Exception as e:
        raise


async def email_students(topic):
    service = authenticate_gmail()
    students_df = pd.read_excel('students.xlsx')
    sender_email = 'uswdrive2024@gmail.com'

    for index, row in students_df.iterrows():
        student_name = row['Name']
        student_email = row['Email']

        # Generate email content
        email_body = generate_email_content(student_name, topic)

        # Create email message
        message = create_message(sender_email, student_email, topic, email_body)

        # Send email
        send_message(service, 'me', message)

        return message


def generate_email_content(student_name, email_subject):
    prompt = f"Write an email to a student named {student_name} with not more than 2 sentences for the following topic: {email_subject}"
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": "You are a teacher that writes email to students on multiple topics"},
            {"role": "user", "content": prompt}
        ]
    )
    email_content = response.choices[0].message.content
    return email_content


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=4000)
