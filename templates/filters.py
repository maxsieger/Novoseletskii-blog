from jinja2 import Environment

def truncate(s, length=255, killwords=False, end='...'):
    if len(s) <= length:
        return s
    return s[:length] + end

def register_filters(app):
    env = app.jinja_env
    env.filters['truncate'] = truncate