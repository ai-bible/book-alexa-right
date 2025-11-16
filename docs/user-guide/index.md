# Руководство пользователя

Это руководство покажет вам, как использовать AI Writing System для создания научно-фантастического романа.

## Основные рабочие процессы

<div class="grid cards" markdown>

-   :material-chart-timeline:{ .lg .middle } __Planning Workflow__

    ---

    Интерактивное планирование от стратегии акта до детальных blueprints

    [:octicons-arrow-right-24: Изучить](planning/workflow-overview.md)

-   :material-creation:{ .lg .middle } __Generation Workflow__

    ---

    7-шаговый процесс создания качественной литературной прозы

    [:octicons-arrow-right-24: Изучить](generation/workflow-overview.md)

-   :material-source-branch:{ .lg .middle } __Session Management__

    ---

    Версионирование и безопасные эксперименты с сюжетом

    [:octicons-arrow-right-24: Изучить](sessions/index.md)

-   :material-database:{ .lg .middle } __Context Management__

    ---

    Управление миром, персонажами и сюжетными линиями

    [:octicons-arrow-right-24: Изучить](context/index.md)

</div>

## Быстрая навигация

### Планирование

| Задача | Команда | Документация |
|--------|---------|--------------|
| Создать план акта/главы/сцены | `/plan-story` | [Planning Workflow](planning/workflow-overview.md) |
| Управлять сюжетными линиями | `/storyline` | [Storylines](planning/storylines.md) |
| Проверить консистентность | `/check-consistency` | [Consistency](commands/consistency-check.md) |

### Генерация

| Задача | Команда | Документация |
|--------|---------|--------------|
| Сгенерировать сцену | `Сгенерируй сцену {ID}` | [Generation Workflow](generation/workflow-overview.md) |
| Проверить статус | `/generation-state status {ID}` | [Generation State](commands/generation-state.md) |
| Восстановить после сбоя | `/generation-state resume {ID}` | [Recovery](generation/error-handling.md) |

### Сессии

| Задача | Команда | Документация |
|--------|---------|--------------|
| Создать сессию | `/session-create {name}` | [Creating Sessions](sessions/creating-sessions.md) |
| Активировать сессию | `/session-activate {name}` | [Branching](sessions/branching.md) |
| Объединить сессии | `/session-merge {from} {to}` | [Merging](sessions/branching.md#merging) |

## Типичные сценарии использования

### Сценарий 1: Написание новой главы

1. **Планирование главы**

    ```
    /plan-story
    ```

    Выберите "Chapter" scope, пройдите 5 фаз планирования.

2. **Планирование сцен**

    Для каждой сцены в главе повторите `/plan-story` с "Scene" scope.

3. **Генерация текста**

    ```
    Сгенерируй сцену 0201
    Сгенерируй сцену 0202
    ...
    ```

4. **Проверка и ревизия**

    Прочитайте сгенерированный текст, внесите правки вручную.

### Сценарий 2: Эксперимент с альтернативной концовкой

1. **Создать ветку**

    ```
    /session-create alt-ending
    /session-activate alt-ending
    ```

2. **Изменить планы**

    Отредактируйте blueprints для альтернативной концовки.

3. **Сгенерировать**

    ```
    Сгенерируй сцену 0901
    ```

4. **Сравнить результаты**

    Переключитесь на main для сравнения:

    ```
    /session-activate main
    ```

5. **Выбрать лучший вариант**

    Если альтернатива лучше, слейте обратно:

    ```
    /session-merge alt-ending main
    ```

### Сценарий 3: Добавление нового персонажа

1. **Создать character card**

    Создайте `context/characters/{name}.md` с детальным описанием.

2. **Обновить сюжетные линии**

    ```
    /storyline add {character-name}
    ```

3. **Обновить blueprints**

    Добавьте персонажа в соответствующие scene blueprints.

4. **Проверить консистентность**

    ```
    /check-consistency
    ```

5. **Регенерировать сцены**

    Для сцен с новым персонажем повторите генерацию.

## Лучшие практики

!!! tip "Планирование перед генерацией"

    **Всегда** создавайте детальный blueprint перед генерацией. Чем больше деталей в blueprint, тем качественнее результат.

!!! tip "Утверждайте verification plan"

    Внимательно читайте verification plan в Step 3. Это ваша последняя возможность убедиться, что система проверит нужные аспекты.

!!! tip "Используйте сессии для экспериментов"

    Не бойтесь экспериментировать в отдельных сессиях. Copy-on-Write гарантирует, что main останется нетронутым.

!!! tip "Регулярный backup"

    Коммитьте изменения в Git после каждой успешной генерации:

    ```bash
    git add .
    git commit -m "Generated scene 0204"
    git push
    ```

!!! tip "Управляйте контекстом"

    Используйте `/compact` между фазами для оптимизации контекстного окна.

!!! warning "Не пропускайте validation"

    Если validation warnings появляются, **не игнорируйте** их. Исправьте проблемы перед продолжением.

!!! warning "Canon levels имеют значение"

    Изменение элементов Level 0-1 требует пересмотра всего романа. Будьте осторожны!

## Дальнейшее изучение

<div class="grid cards" markdown>

-   [:octicons-workflow-24: Planning Details](planning/index.md)
-   [:octicons-gear-24: Generation Details](generation/index.md)
-   [:octicons-command-palette-24: All Commands](commands/index.md)
-   [:octicons-database-24: Context System](context/index.md)

</div>
