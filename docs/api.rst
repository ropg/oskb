API
---

Want to show a keyboard as part of your messaging app, embedded project or some other Qt project? ``oskb.Keyboard(QWidget)`` is a Qt ``QWidget`` that you can use in your own code. It shows a keyboard and can either handle the keypress events at various levels itself or be told what function should handle them externally. Both ``oskb`` and ``oskbedit`` rely on this widget, using it in different ways.
