"""
Agent definitions for the Course Content Generator.

Each agent has a specific role in the content creation pipeline:
- Curriculum Architect: Plans structure and learning objectives
- Content Writer: Creates lesson content and code examples  
- Quiz Master: Designs assessment questions and exercises
- Code Reviewer: Ensures code quality and accuracy
"""

from crewai import Agent, LLM
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
import os


deepseek_llm = LLM(
    model="deepseek/deepseek-v4-flash",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
)
def create_web_researcher() -> Agent:
    """
    搜索与课程主题有关的最新、可靠资料，
    为后面的课程设计和内容写作提供事实依据。
    """
    return Agent(
        role="Web Research Specialist",
        goal=(
            "Research current, accurate, and authoritative information about "
            "the course topic, and produce a structured research brief with sources"
        ),
        backstory=(
            "You are a careful technical researcher. You search broadly, prefer "
            "official documentation and primary sources, compare multiple sources, "
            "and never present unsupported claims as facts. Your findings will be "
            "used by curriculum designers and technical writers."
        ),
        llm=deepseek_llm,
        tools=[
            SerperDevTool(n_results=5),
            ScrapeWebsiteTool(),
        ],
        max_iter=4,
        max_execution_time=120,
        max_retry_limit=1,
        cache=True,
        verbose=True,  #详细的输出模式
        allow_delegation=False,  #不允许委派给其他任务
    )
def create_curriculum_architect() -> Agent:
    """
    Creates the Curriculum Architect agent.
    
    This agent is responsible for:
    - Analyzing the topic and breaking it into learnable chunks
    - Defining clear, measurable learning objectives
    - Creating a logical lesson structure
    - Identifying prerequisites and dependencies
    """
    return Agent(
        role="Curriculum Architect",
        goal=(
            "Design a comprehensive and well-structured lesson plan that guides "
            "learners from foundational concepts to practical application"
        ),
        backstory=(
            "You are an experienced instructional designer with deep expertise in "
            "technical education. You've designed curricula for major tech companies "
            "and online learning platforms. You understand how developers learn best: "
            "through clear explanations, practical examples, and hands-on practice. "
            "You specialize in breaking down complex topics into digestible chunks "
            "while maintaining technical accuracy."
        ),
        llm=deepseek_llm,
        max_iter=2,
        max_execution_time=120,
        max_retry_limit=1,
        cache=True,
        verbose=True,
        allow_delegation=False,
    )


def create_content_writer() -> Agent:
    """
    Creates the Content Writer agent.
    
    This agent is responsible for:
    - Writing clear, engaging lesson content
    - Creating practical code examples
    - Explaining concepts with appropriate depth
    - Using consistent tone and terminology
    """
    return Agent(
        role="Technical Content Writer",
        goal=(
            "Create clear, engaging, and technically accurate lesson content "
            "with practical code examples that developers can immediately use"
        ),
        backstory=(
            "You are a senior technical writer who has authored documentation for "
            "popular open-source projects and developer tools. You have a gift for "
            "explaining complex concepts in simple terms without dumbing them down. "
            "Your code examples are always production-quality: well-commented, "
            "following best practices, and actually runnable. You write in a "
            "conversational but professional tone that keeps developers engaged."
        ),
        llm=deepseek_llm,
        max_iter=2,
        max_execution_time=120,
        max_retry_limit=1,
        cache=True,
    verbose=True,
        allow_delegation=False,
    )


def create_quiz_master() -> Agent:
    """
    Creates the Quiz Master agent.
    
    This agent is responsible for:
    - Creating varied assessment questions
    - Designing hands-on exercises
    - Ensuring questions test understanding, not memorization
    - Providing helpful explanations for answers
    """
    return Agent(
        role="Quiz Master",
        goal=(
            "Design assessment questions and exercises that truly test "
            "understanding and reinforce learning through practical application"
        ),
        backstory=(
            "You are an assessment specialist who has created certification exams "
            "and course assessments for major tech education platforms. You believe "
            "the best questions test conceptual understanding and practical skills, "
            "not rote memorization. Your exercises are challenging but achievable, "
            "building confidence while pushing learners to apply what they've learned. "
            "You always explain why answers are correct or incorrect."
        ),
        llm=deepseek_llm,
        max_iter=2,
        max_execution_time=120,
        max_retry_limit=1,
        cache=True,
        verbose=True,
        allow_delegation=False,
    )


def create_code_reviewer() -> Agent:
    """
    Creates the Code Reviewer agent.
    
    This agent is responsible for:
    - Reviewing all code examples for correctness
    - Ensuring code follows best practices
    - Checking for common mistakes and anti-patterns
    - Suggesting improvements for clarity
    """
    return Agent(
        role="Senior Code Reviewer",
        goal=(
            "Ensure all code examples are correct, follow best practices, "
            "and demonstrate proper patterns that learners should emulate"
        ),
        backstory=(
            "You are a senior software engineer with 15+ years of experience who "
            "now focuses on code quality and developer education. You've reviewed "
            "thousands of pull requests and have a keen eye for spotting bugs, "
            "anti-patterns, and opportunities for improvement. You're particularly "
            "experienced with Python and the CrewAI framework. Your reviews are "
            "thorough but constructive, always explaining the 'why' behind your "
            "suggestions."
        ),
        llm=deepseek_llm,
        max_iter=2,
        max_execution_time=120,
        max_retry_limit=1,
        cache=True,
        verbose=True,
        allow_delegation=False,
    )


def get_all_agents() -> dict[str, Agent]:
    """
    Create and return all agents as a dictionary.
    
    Returns:
        Dictionary mapping agent names to Agent instances
    """
    return {
        "web_researcher": create_web_researcher(),
        "curriculum_architect": create_curriculum_architect(),
        "content_writer": create_content_writer(),
        "quiz_master": create_quiz_master(),
        "code_reviewer": create_code_reviewer(),
    }
