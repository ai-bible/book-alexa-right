import os
from github import Github
import yaml
from datetime import datetime, timedelta

def create_github_roadmap(token, repo_name, roadmap_data):
    # Initialize GitHub connection
    g = Github(token)
    
    # Get repo directly - works for both user and org repos
    repo = g.get_repo(repo_name)
    
    # Create milestones
    milestones = {}
    start_date = datetime.now()
    
    for stage in roadmap_data:
        # Calculate due date
        weeks = sum([int(duration.split('-')[0]) for duration in stage.get('duration', ['2-3']).split()])
        due_date = start_date + timedelta(weeks=weeks)
        
        # Create milestone
        milestone = repo.create_milestone(
            title=stage['title'],
            state='open',
            description=stage.get('description', ''),
            due_on=due_date
        )
        
        milestones[stage['id']] = milestone
        start_date = due_date
        
        # Create issues for this milestone
        for task in stage.get('tasks', []):
            issue = repo.create_issue(
                title=task['title'],
                body=task.get('description', ''),
                milestone=milestone
            )
            
            # Add labels if specified
            if 'labels' in task:
                issue.add_to_labels(*task['labels'])
    
    print(f"Created roadmap with {len(milestones)} milestones and {sum([len(stage.get('tasks', [])) for stage in roadmap_data])} issues")

# Define the roadmap data
roadmap_yaml = """
- id: foundation
  title: "Этап 1: Фундамент"
  description: "Разработка базовой структуры приложения и системы хранения"
  duration: "2-3"
  tasks:
    - title: "Разработать базовую структуру приложения"
      description: "Создание проекта, настройка окружения и разработка архитектуры приложения."
      labels: ["foundation", "high-priority"]
    
    - title: "Создать систему хранения Markdown-файлов"
      description: "Реализация механизма хранения и организации Markdown-файлов с библией мира и каноном."
      labels: ["storage", "markdown"]
    
    - title: "Реализовать парсер Markdown и таблиц"
      description: "Создание компонента для парсинга Markdown, особенно таблиц с данными библии мира."
      labels: ["markdown", "parser"]
    
    - title: "Разработать базовый редактор с подсветкой синтаксиса"
      description: "Создание UI-компонента для редактирования Markdown с подсветкой синтаксиса."
      labels: ["ui", "editor"]
    
    - title: "Создать MVP системы версионирования"
      description: "Реализация хранения X последних версий файлов с возможностью настройки количества."
      labels: ["versioning"]

- id: mcp_templates
  title: "Этап 2: MCP и шаблоны"
  description: "Разработка MCP-интерфейса и системы шаблонизации промптов"
  duration: "2-3"
  tasks:
    - title: "Разработать API MCP-интерфейса"
      description: "Создание API для взаимодействия с ИИ-моделями и получения запросов на контексты."
      labels: ["api", "mcp", "high-priority"]
    
    - title: "Создать базовую библиотеку шаблонов промптов"
      description: "Разработка начального набора шаблонов для различных задач (сцены, персонажи, локации)."
      labels: ["templates", "prompts"]
    
    - title: "Реализовать механизм переменных в шаблонах"
      description: "Создание системы подстановки переменных и контекстов в шаблоны промптов."
      labels: ["templates", "variables"]
    
    - title: "Интегрировать шаблонизатор с MCP-интерфейсом"
      description: "Объединение системы шаблонов с MCP для автоматической подстановки запрашиваемых контекстов."
      labels: ["integration", "mcp", "templates"]
    
    - title: "Разработать UI для управления шаблонами"
      description: "Создание интерфейса для создания, редактирования и версионирования шаблонов промптов."
      labels: ["ui", "templates"]

- id: content_management
  title: "Этап 3: Работа с контентом"
  description: "Реализация импорта/экспорта и анализа содержимого"
  duration: "2-3"
  tasks:
    - title: "Реализовать импорт/экспорт Markdown-файлов"
      description: "Создание механизмов для импорта существующих и экспорта обновленных Markdown-файлов."
      labels: ["import", "export", "markdown"]
    
    - title: "Создать систему отслеживания изменений в библии мира"
      description: "Разработка компонента для мониторинга и выделения изменений в библии мира."
      labels: ["tracking", "world-bible"]
    
    - title: "Разработать механизм проверки на противоречия с каноном"
      description: "Создание системы для анализа новых элементов на соответствие установленному канону."
      labels: ["validation", "canon", "high-priority"]
    
    - title: "Реализовать полуавтоматический анализ новых элементов"
      description: "Разработка помощника для извлечения новых элементов мира из сгенерированного текста."
      labels: ["analysis", "extraction"]
    
    - title: "Интегрировать все компоненты в единый интерфейс"
      description: "Объединение всех разработанных компонентов в целостный пользовательский интерфейс."
      labels: ["integration", "ui"]

- id: testing_finalization
  title: "Этап 4: Тестирование и доработка"
  description: "Тестирование и финализация MVP"
  duration: "1-2"
  tasks:
    - title: "Провести тестирование на реальных сценариях использования"
      description: "Тестирование MVP с реальными данными и сценариями использования."
      labels: ["testing", "high-priority"]
    
    - title: "Оптимизировать работу с большими файлами"
      description: "Улучшение производительности при работе с большими Markdown-файлами и библией мира."
      labels: ["optimization", "performance"]
    
    - title: "Доработать UX на основе обратной связи"
      description: "Улучшение пользовательского опыта на основе полученной обратной связи."
      labels: ["ux", "feedback"]
    
    - title: "Исправить выявленные ошибки"
      description: "Фиксация багов и проблем, найденных во время тестирования."
      labels: ["bugfix"]
    
    - title: "Подготовить документацию по использованию MVP"
      description: "Создание руководства пользователя и технической документации для MVP."
      labels: ["documentation"]
"""

def main():
    # Get GitHub token from environment variable or input
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        token = input("Enter your GitHub token: ")
    
    # Get repository name
    repo_name = input("Enter repository name (e.g., username/repo): ")
    
    # Load roadmap data
    roadmap_data = yaml.safe_load(roadmap_yaml)
    
    # Create roadmap in GitHub
    create_github_roadmap(token, repo_name, roadmap_data)

if __name__ == "__main__":
    main()