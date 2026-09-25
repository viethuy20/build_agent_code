from setuptools import setup

setup(
    name="susu",
    version="0.3.0",
    description="Susu — Multi-Agent AI Software Engineering CLI",
    author="viethuy20",
    py_modules=[
        "main",
        "planner",
        "agy_worker",
        "git_manager",
        "test_runner",
        "logger",
        "subagent_roles",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "susu = main:main",
        ],
    },
)
