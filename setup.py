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
        "knowledge_manager",
        "notebooklm_bridge",
    ],
    package_data={
        "": ["skills/*/*.md"],
    },
    include_package_data=True,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "susu = main:main",
        ],
    },
)
