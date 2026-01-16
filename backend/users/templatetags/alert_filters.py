from django import template

register = template.Library()

@register.filter(name='bootstrap_alert_class')
def bootstrap_alert_class(tag):
    return 'danger' if tag == 'error' else tag