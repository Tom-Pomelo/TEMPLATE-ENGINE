from builder import *
import re


class Template(object):
    def __init__(self, text, *contexts):
        self.context = {}
        for context in contexts:
            self.context.update(context)

        self.all_variables = set()
        self.loop_variables = set()

        code = CodeBuilder()

        code.add_line('def render_function(context, do_dots):')
        code.indent()

        section = code.add_section()

        code.add_line('result = []')
        code.add_line('append_result = result.append')
        code.add_line('extend_result = result.extend')
        code.add_line('to_str = str')

        buffered = []

        def flush_output():
            if len(buffered) == 1:
                code.add_line('append_result(%s)' % buffered[0])
            elif len(buffered) > 1:
                code.add_line('extend_result([%s])' % ", ".join(buffered))
            del buffered[:]

        ops_stack = []

        tokens = re.split(r'(?s)({{.*?}}|{%.*?%}|{#.*?#})', text)
        for token in tokens:
            if tokens.startswith('#'):
                # comment
                continue
            elif tokens.startswith('{{'):
                # eg: {{ name }}
                expr = self._expr_code(tokens[2:-2].strip())
                buffered.append('to_str(%s)' % expr)
            elif tokens.startswith('{%'):
                # eg: {% for t in topics %}
                flush_output()
                words = tokens[2:-2].strip().split()
                if words[0] == 'if':
                    if len(words) != 2:
                        self._syntax_error('Don\'t understand if', token)
                    ops_stack.append('if')
                    code.add_line("if %s" % self._expr_code(words[1]))
                    code.indent()
                elif words[0] == 'for':
                    if len(words) != 4 or words[2] != 'in':
                        self._syntax_error('Don\'t understand for', token)
                    ops_stack.append('for')
                    self._variable(words[1], self.loop_variables)
                    code.add_line('for c_%s %s %s' %
                                  (words[1], words[2], self._expr_code(words[3])))
                    code.indent()
                elif words[0].startswith('end'):
                    # eg: endfor / endif
                    if len(words) != 1:
                        self._syntax_error('Don\'t understand end', token)
                    ops_end = words[0][3:]
                    if not ops_stack:
                        self._syntax_error('Too many ends', token)
                    ops_start = ops_stack.pop()
                    if ops_start != ops_end:
                        self._syntax_error('Mismatch ending tag', ops_end)
                    code.dedent()
                else:
                    self._syntax_error('Don\'t understand tag', words[0])
            else:
                # literal content
                if token:
                    buffered.append(repr(token))
        if ops_stack:
            self._syntax_error('Unmatched action tag', ops_stack[-1])

        flush_output()

        for var in self.all_variables - self.loop_variables:
            section.add_line('c_%s = context[%r]' % (var, var))

        code.add_line('return \'\'.join(result)')
        code.dedent()
        self._render_function = code.get_globals()['render_function']

    def _expr_code(self, expr):
        if '|' in expr:
            # eg:
            pipes = expr.split('|')
            code = self._expr_code(pipes[0])
            for fn in pipes[1:]:
                self._variable(fn, self.all_variables)
                code = 'c_%s(%s)' % (fn, code)
        elif '.' in expr:
            # eg: course.student.id
            dots = expr.split('.')
            code = self._expr_code(dots[0])
            args = ', '.join(repr(d) for d in dots[1:])
            code = 'do_dots(%s, %s)' % (code, args)
        else:
            self._variable(expr, self.all_variables)
            code = "c_%s" % expr
        return code

    def _syntax_error(self, msg, at):
        raise ValueError('%s %r', (msg, at))

    def _variable(self, name, variables_set):
        if not re.match(r'[_a-zA-Z][_a-zA-Z0-9]*$', name):
            self._syntax_error('Not a valid name', name)
        variables_set.add(name)

    def render(self, context=None):
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        self._render_function(render_context, self._do_dots)

    def _do_dots(self, value, *dots):
        # course.student.id
        # check if course[student][id] or course[student[id]]
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value
