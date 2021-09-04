project_name = ask('project_name', 'Gimmi yo project name')
author = ask('author', 'Who you?')
readme_type = ask('readme_type', 'type of readme ya\'like', 0, choices=["Markdown", "reStructuredText"])
readme_ext = 'md' if readme_type == "Markdown" else 'rst'
python_ver = ask('python_ver', 'Python yo!', '^3.6')
build_system_req = ask('build_system_req', 'Build System??', 'relaxed-poetry-core>=0.0.7')


