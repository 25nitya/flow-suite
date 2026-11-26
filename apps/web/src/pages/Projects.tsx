import { useEffect, useState, type FormEvent } from "react";
import { api, type Project, type Task } from "../api";

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [name, setName] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [error, setError] = useState("");

  async function loadProjects() {
    const list = await api.projects();
    setProjects(list);
    if (!selected && list[0]) setSelected(list[0].id);
  }

  async function loadTasks(pid: string) {
    setTasks(await api.tasks(pid));
  }

  useEffect(() => {
    loadProjects().catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (selected) loadTasks(selected).catch((e) => setError(e.message));
  }, [selected]);

  async function createProject(e: FormEvent) {
    e.preventDefault();
    try {
      await api.createProject({ name });
      setName("");
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function createTask(e: FormEvent) {
    e.preventDefault();
    if (!selected) return;
    try {
      await api.createTask(selected, { title: taskTitle });
      setTaskTitle("");
      await loadTasks(selected);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <div>
      <h1>Projects & tasks</h1>
      {error && <p className="error">{error}</p>}
      <div className="split">
        <section>
          <form className="inline-form" onSubmit={createProject}>
            <input placeholder="Project name" value={name} onChange={(e) => setName(e.target.value)} required />
            <button className="cta" type="submit">
              Create
            </button>
          </form>
          <ul className="list">
            {projects.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  className={selected === p.id ? "selected" : ""}
                  onClick={() => setSelected(p.id)}
                >
                  {p.name}
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() =>
                    api
                      .deleteProject(p.id)
                      .then(loadProjects)
                      .catch((e) => setError(e.message))
                  }
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h2>Tasks</h2>
          <form className="inline-form" onSubmit={createTask}>
            <input
              placeholder="Task title"
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              required
            />
            <button className="cta" type="submit">
              Add task
            </button>
          </form>
          <ul className="task-board">
            {tasks.map((t) => (
              <li key={t.id}>
                <strong>{t.title}</strong>
                <select
                  value={t.status}
                  onChange={(e) =>
                    api
                      .updateTask(t.id, { status: e.target.value })
                      .then(() => loadTasks(selected))
                      .catch((err) => setError(err.message))
                  }
                >
                  <option value="todo">todo</option>
                  <option value="doing">doing</option>
                  <option value="done">done</option>
                </select>
                <button
                  type="button"
                  className="ghost"
                  onClick={() =>
                    api
                      .deleteTask(t.id)
                      .then(() => loadTasks(selected))
                      .catch((err) => setError(err.message))
                  }
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
