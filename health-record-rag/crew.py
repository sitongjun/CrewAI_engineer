"""CrewAI crew definition using the official 1.15.18 tools."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from tools.pdf_search import create_pdf_search_tool
from tools.report_writer import create_report_writer_tool


@CrewBase
class CrewtestprojectCrew:
    """A two-agent health-record RAG crew."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, model):
        self.model = model
        self.pdf_search_tool = create_pdf_search_tool()
        self.file_writer_tool = create_report_writer_tool()

    @agent
    def retrieval_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["retrieval_agent"],
            llm=self.model,
            tools=[self.pdf_search_tool],
            allow_delegation=False,
            max_iter=3,
            verbose=True,
        )

    @agent
    def report_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["report_agent"],
            llm=self.model,
            tools=[self.file_writer_tool],
            allow_delegation=False,
            max_iter=3,
            verbose=True,
        )

    @task
    def retrieval_task(self) -> Task:
        return Task(config=self.tasks_config["retrieval_task"])

    @task
    def report_task(self) -> Task:
        return Task(config=self.tasks_config["report_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            cache=True,
        )
