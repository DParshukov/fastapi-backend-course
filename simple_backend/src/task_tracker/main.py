import os
import json
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = os.getenv("GIST_ID")
if not GITHUB_TOKEN or not GIST_ID:
    raise RuntimeError("Please set GITHUB_TOKEN and GIST_ID environment variables")
API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


class GitStorage:
    def __init__(self, file: str = "task.json"):
        self.file = file

    filename = "task.json"

    def _get_gist(self):
        resp = requests.get(API_URL, headers=HEADERS)
        if resp.status_code != 200:
            raise HTTPException(resp.status_code, "Cannot fetch Gist")
        return resp.json()

    def load(self):
        gist = self._get_gist()
        file = gist.get("files", {})
        content = file.get(self.file, {}).get("content")
        if content is None:
            return []
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(500, "Invalid JSON in Gist")

    def save(self, tasks):
        body = {
            "files": {
                self.filename: {
                    "content": json.dumps(tasks, ensure_ascii=False, indent=2)
                }
            }
        }
        resp = requests.patch(API_URL, headers=HEADERS, json=body)
        if resp.status_code not in (200, 201):
            raise HTTPException(resp.status_code, "Cannot update Gist")
        return resp.json()


storag = GitStorage()


@app.get("/tasks")
def get_tasks():
    return storag.load()


@app.post("/tasks")
def create_task(task: dict):
    tasks = storag.load()
    new_id = max([t.get("id", 0) for t in tasks] or [0]) + 1
    task["id"] = new_id
    tasks.append(task)
    storag.save(tasks)
    return task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: dict):
    tasks = storag.load()
    for t in tasks:
        if t["id"] == task_id:
            t.update(task)
            storag.save(tasks)
            return t
    return "No tasks"


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    tasks = storag.load()
    new = [t for t in tasks if t.get("id") != task_id]
    if len(new) == len(tasks):
        return {"detail": "Task not found"}
    storag.save(new)
    return {"detail": f"Task {task_id} deleted"}
