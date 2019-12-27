class CodeBuilder(object):
    def __init__(self, indent = 0):
        self.code = []
        self.indent_level = indent

    def add_line(self, line):
        self.code.extend([' ' * self.indent_level, line, '\n'])

    def add_section(self):
        section = CodeBuilder(self.indent_level)
        self.code.append(section)
        return section

    INDENT_STEP = 4

    def indent(self):
        self.indent_level += self.INDENT_STEP

    def dedent(self):
        self.indent_level -= self.INDENT_STEP

    def __str__(self):
        return ''.join(str(c) for c in self.code)

    def get_globals(self):
        assert self.indent_level == 0
        src = str(self)
        global_namespace = {}
        exec(src, global_namespace)
        return global_namespace
