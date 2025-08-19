---
title: "Minimal Shiny Python"
format: html
engine: shiny
---

```{python}
from shiny import App, ui, render

app_ui = ui.page_fluid(
    ui.input_text("text", "Enter some text"),
    ui.input_action_button("go", "Show"),
    ui.output_text("result")
)

def server(input, output, session):
    @output
    @render.text
    def result():
        if input.go() == 0:
            return ""
        return f"You entered: {input.text()}"

app = App(app_ui, server)
```
