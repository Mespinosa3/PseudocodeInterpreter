import sys
from PyQt5.QtWidgets import *
from PyQt5 import Qt
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from pathlib import Path
import operator
from sly import Lexer, Parser
from qt_material import apply_stylesheet

# lexer
class MyLexer(Lexer):
    # Set of token names (NOTE: sets are a built-in python data structure which store multiple values under a single name)
    tokens = {
        NEWLINE,
        TRUE,
        FALSE,
        ID, 
        INT, 
        FLOAT,
        EQUAL,
        UNEQUAL,
        GREATEREQUAL,
        LESSEQUAL,
        GREATER,
        LESS, 
        ASSIGN, 
        STRINGSINGLE, 
        STRINGDOUBLE,
        IF, 
        THEN,
        ELSE, 
        ENDIF,
        WHILE,
        ENDWHILE,
        REPEAT,
        UNTIL,
        FOR,
        TO,
        STEP,
        NEXT,
        OUTPUT,
        BEGIN, 
        END,
    }

    # string literals to make precedence clearer
    literals = {
        '+', '-', '*', '/', '(', ')', '[', ']', ':', ','
    }

    # Characters to ignore while lexing
    ignore = '\t '

    # regexes
    NEWLINE = r'\n+'
    TRUE = r'true'
    FALSE = r'false'
    STRINGSINGLE = r"\'.*?\'"
    STRINGDOUBLE = r'\".*?\"'
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
    FLOAT = r'[0-9]+[.][0-9]*'
    INT = r'\d+'
    EQUAL = r'=='
    UNEQUAL = r'<>'
    GREATEREQUAL = r'>='
    LESSEQUAL = r'<='
    GREATER = r'>'
    LESS = r'<'
    ASSIGN = r'='

    # special cases
    ID['IF'] =  IF
    ID['THEN'] = THEN
    ID['ENDIF'] = ENDIF
    ID['ELSE'] = ELSE
    ID['WHILE'] = WHILE
    ID['ENDWHILE'] = ENDWHILE
    ID['REPEAT'] = REPEAT
    ID['UNTIL'] = UNTIL
    ID['FOR'] = FOR
    ID['TO'] = TO
    ID['STEP'] = STEP
    ID['NEXT'] = NEXT
    ID['Print'] = OUTPUT
    ID['Display'] = OUTPUT
    ID['BEGIN'] = BEGIN
    ID['END'] = END

    @_ (r'\n+')
    def newline(self, t):
        self.lineno += t.value.count('\n')

# parser
class MyParser(Parser):
    # tokens are passed from lexer to parser
    tokens = MyLexer.tokens

    # precedence
    precedence = (
        ('nonassoc', LESS, GREATER, UNEQUAL, EQUAL, LESSEQUAL, GREATEREQUAL),
        ('left', '+', '-'),
        ('left', '*', '/'),
        ('right', UMINUS),
    )

    # sets the environment of the parser. This is a feature of the SLY module which is used to store variables and functions when executing
    def __init__(self):
        self.env = { }

    # Grammar rules
    # program
    @_('BEGIN NEWLINE statement NEWLINE END', 
        'BEGIN NEWLINE statements NEWLINE END')
    def program(self, p):
        return ('program', p[2])

    # if statements
    @_('IF condition THEN NEWLINE statements NEWLINE ELSE NEWLINE statements NEWLINE ENDIF',
        'IF condition THEN NEWLINE statement NEWLINE ELSE NEWLINE statement NEWLINE ENDIF',
        'IF condition THEN NEWLINE statement NEWLINE ELSE NEWLINE statements NEWLINE ENDIF',
        'IF condition THEN NEWLINE statements NEWLINE ELSE NEWLINE statement NEWLINE ENDIF')
    def statement(self, p):
        return ('if_else_statement', p.condition, p[4], p[8])

    @_('IF condition THEN NEWLINE statements NEWLINE ENDIF',
        'IF condition THEN NEWLINE statement NEWLINE ENDIF')
    def statement(self, p):
        return ('if_statement', p.condition, p[4])

    # loops
    @_('FOR var_assign TO expr STEP expr NEWLINE statements NEWLINE NEXT ID',
    'FOR var_assign TO expr STEP expr NEWLINE statement NEWLINE NEXT ID',)
    def statement(self, p):
        return ('for_step', p.var_assign, p.expr0, p.expr1, p[7], p.ID)
    
    @_('FOR var_assign TO expr NEWLINE statement NEWLINE NEXT ID',
        'FOR var_assign TO expr NEWLINE statements NEWLINE NEXT ID',)
    def statement(self, p):
        return ('for', p.var_assign, p.expr, p[5], p.ID)

    @_('WHILE condition NEWLINE statements NEWLINE ENDWHILE',
        'WHILE condition NEWLINE statement NEWLINE ENDWHILE')
    def statement(self, p):
        return ('while', p.condition, p[3])

    @_('REPEAT NEWLINE statements NEWLINE UNTIL condition',
        'REPEAT NEWLINE statement NEWLINE UNTIL condition')
    def statement(self, p):
        return ('repeat', p[2], p.condition)

    # statements
    @_('statements NEWLINE statement',
        'statement NEWLINE statement')
    def statements(self, p):
        return ('statements', p[0], p[2])

    # conditions
    @_('expr operator expr')
    def condition(self, p):
        return ('condition', p.operator, p[0], p[2])

    @_('EQUAL',
        'UNEQUAL',
        'GREATEREQUAL',
        'LESSEQUAL',
        'GREATER',
        'LESS')
    def operator(self, p):
        return ('operator', p[0])
    
    # variable assignment
    @_('var_assign')
    def statement(self, p):
        return p.var_assign

    @_('ID ASSIGN expr')
    def var_assign(self, p):
        return ('var_assign', p.ID, p.expr)

    @_('ID ASSIGN string')
    def var_assign(self, p):
        return ('var_assign', p.ID, p.STRING)

    # outputs
    @_('OUTPUT expr',
        'OUTPUT string',
        'OUTPUT boolean',)
    def statement(self, p):
        return ('output', p[1])

    # expressions
    @_('expr "+" expr')
    def expr(self, p):
        return ('add', p.expr0, p.expr1)

    @_('expr "-" expr')
    def expr(self, p):
        return ('sub', p.expr0, p.expr1)

    @_('expr "*" expr')
    def expr(self, p):
        return ('mul', p.expr0, p.expr1)

    @_('expr "/" expr')
    def expr(self, p):
        return ('div', p.expr0, p.expr1)

    @_('"-" expr %prec UMINUS')
    def expr(self, p):
        return ('u_minus', p.expr)

    @_('ID')
    def expr(self, p):
        return ('var', p.ID)

    @_('INT')
    def expr(self, p):
        return ('int', p.INT)

    @_('FLOAT')
    def expr(self, p):
        return ('float', p.FLOAT)

    @_('TRUE')
    def boolean(self, p):
        return ('bool', p.TRUE)
    
    @_('FALSE')
    def boolean(self, p):
        return ('bool', p.FALSE)

    # string expressions: these are used to reduce the two string tokens into a single string type
    @_('string "+" string')
    def string(self, p):
        return ('concatenate', p[0], p[2])
    
    @_('STRINGSINGLE')
    def string(self, p):
        return (p.STRINGSINGLE)

    @_('STRINGDOUBLE')
    def string(self, p):
        return ('str', p.STRINGDOUBLE)

class Execute:
    def __init__(self, tree, env):
        self.env = env
        self.output = []
        self.result = self.walkTree(tree)
        
        
    def walkTree(self, node):
        self.operator_table = {
            '<': operator.lt,
            '<=': operator.le,
            '==': operator.eq,
            '<>': operator.ne,
            '>=': operator.ge,
            '>': operator.gt
        }

        if node is None:
            return None



        if node[0] == 'program':
            return self.walkTree(node[1])
                
        if node[0] == 'int':
            return int(node[1])

        if node[0] == 'float':
            return float(node[1])

        if node[0] == 'str':
            return node[1]

        if node[0] == 'bool':
            return node[1]

        if node[0] == 'if_statement':
            result = self.walkTree(node[1])
            if result:
                return self.walkTree(node[2])

        if node[0] == 'if_else_statement':
            result = self.walkTree(node[1])
            if result:
                return self.walkTree(node[2])
            else:
                return self.walkTree(node[3])

        if node[0] == 'for_step':
            if node[5] == node[1][1]:
                for self.env[node[1][1]] in range(self.env[self.walkTree(node[1])], self.walkTree(node[2]), self.walkTree(node[3])):
                    result = self.walkTree(node[4])
                del self.env[node[1][1]]
                return result
            else: 
                return('looping error: for loop variable is not identical')

        if node[0] == 'for':
            if node[4] == node[1][1]:
                for self.env[node[1][1]] in range(self.env[self.walkTree(node[1])], self.walkTree(node[2])):
                    result = self.walkTree(node[3])
                del self.env[node[1][1]]
                return result
            else: 
                return('looping error: for loop variable is not identical')

        if node[0] == 'while':
            condition = self.walkTree(node[1])
            while condition:
                result = self.walkTree(node[2])
            return result

        if node[0] == 'repeat':
            condition = self.walkTree(node[1])
            while True:
                result = self.walkTree(node[2])
                if condition:
                    break
                return result

        if node[0] == 'statements':
            return [self.walkTree(node[1]), self.walkTree(node[2])]

        if node[0] == 'condition':
            return(self.operator_table[self.walkTree(node[1])](self.walkTree(node[2]), self.walkTree(node[3])))

        if node[0] == 'operator':
            return node[1]

        if node[0] == 'add':
            return self.walkTree(node[1]) + self.walkTree(node[2])
        elif node[0] == 'sub':
            return self.walkTree(node[1]) - self.walkTree(node[2])
        elif node[0] == 'mul':
            return self.walkTree(node[1]) * self.walkTree(node[2])
        elif node[0] == 'div':
            return self.walkTree(node[1]) / self.walkTree(node[2])
        elif node[0] == 'u_minus':
            return 0-self.walkTree(node[1])

        if node[0] == 'var_assign':
            self.env[node[1]] = self.walkTree(node[2])
            return node[1]

        if node[0] == 'var':
            try:
                return self.env[node[1]]
            except LookupError:
                return("Undefined variable found!")

        if node[0] == 'output':
            self.output.append(self.walkTree(node[1]))

        if node[0] == 'concatenate':
            return (self.walkTree(node[1]) + self.walkTree(node[2]))

class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.title = 'Pseudocode Text Editor'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480

        apply_stylesheet(app, theme='dark_cyan.xml')

        self.initUI()

    # used to create window properties -- very similar to __init__ but does not construct. 
    # basically, constructor creates values, initUI makes values from constructor into properties of the window.
    def initUI(self):

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        # layout editing section
        self.layout.setSpacing(0)

        # text area
        self.textarea = QTextEdit()
        self.textarea.row = 10
        self.textarea.column = 10
        self.textarea.setTabStopWidth(self.textarea.fontMetrics().width(' ') * 4)
        self.textarealabel = QLabel('Code', self)
        self.textarealabel.row = self.textarea.row - 1
        self.textarealabel.column = self.textarea.column

        # Output area
        self.output_area = QTextEdit()
        self.output_area.row = self.textarea.row 
        self.output_area.column = self.textarea.column + 1
        self.output_area.setReadOnly(True)
        self.output_arealabel = QLabel('Output', self)
        self.output_arealabel.row = self.output_area.row - 1
        self.output_arealabel.column = self.output_area.column

        # file box layout
        self.fileButtonsBox = QHBoxLayout()
        self.fileButtonsBox.row = self.textarea.row + 1
        self.fileButtonsBox.column = self.textarea.column 

        # open file button
        self.openbutton = QPushButton('open file', self)
        # signal for open button
        self.openbutton.clicked.connect(self.OpenFileDialog)

        # save open file button
        self.savebutton = QPushButton('save file', self)
        #signal for save file button
        self.savebutton.clicked.connect(self.SaveFileDialog)

        # adding buttons to file buttons box
        self.fileButtonsBox.addWidget(self.openbutton)
        self.fileButtonsBox.addWidget(self.savebutton)

        # run and help buttons box layout
        self.otherButtonsBox = QHBoxLayout()
        self.otherButtonsBox.row = self.textarea.row + 1
        self.otherButtonsBox.column = self.textarea.column + 1

        # run code button
        self.runbutton = QPushButton('Run', self)
        self.runbutton.clicked.connect(self.RunCode)

        # online help button
        self.helpbutton = QPushButton('Help', self)
        self.helpbutton.clicked.connect(self.OnlineHelp)

        # adding buttons to other button box
        self.otherButtonsBox.addWidget(self.runbutton)
        self.otherButtonsBox.addWidget(self.helpbutton)

        # section for adding widgets to layout 
        self.layout.addWidget(self.textarea, self.textarea.row, self.textarea.column)
        self.layout.addWidget(self.output_area, self.output_area.row, self.output_area.column)
        self.layout.addWidget(self.textarealabel, self.textarealabel.row, self.textarealabel.column)
        self.layout.addWidget(self.output_arealabel, self.output_arealabel.row, self.output_arealabel.column)
        self.layout.addLayout(self.fileButtonsBox, self.fileButtonsBox.row, self.fileButtonsBox.column)
        self.layout.addLayout(self.otherButtonsBox, self.otherButtonsBox.row, self.otherButtonsBox.column)

        # show all widgets
        self.show()

    @pyqtSlot()
    def OpenFileDialog(self):
        home_dir = str(Path.home())
        fname = QFileDialog.getOpenFileName(self, 'Open file', home_dir)

        if fname[0]:
            f = open(fname[0], 'r')

            with f:
                data = f.read()
                self.textarea.setText(data)

    @pyqtSlot()
    def SaveFileDialog(self):
        home_dir = str(Path.home())
        fname = QFileDialog.getSaveFileName(self, 'Save file', home_dir)
        Text = self.textarea.toPlainText()

        if fname[0]:
            f = open(fname[0], 'w')

            with f:
                data = f.write(Text)

    # end of file error function
    def EOF(self):
        with open(self.file,'r') as f:
            f.seek(0,2)     # go to the file end.
            return f.tell()   # get the end of file location

    @pyqtSlot()
    def RunCode(self):
        lexer = MyLexer()
        parser = MyParser()
        env = {}
        tree = parser.parse(lexer.tokenize(self.textarea.toPlainText()))
        executed = Execute(tree, env)
        self.output_area.setText(str(executed.output))
        

    @pyqtSlot()
    def OnlineHelp(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Just type your code into the left box and click run to run it. It's that simple! \n\nYou can open any text file into the left box with the open button to start editing it. \n\nYou can also save the file you're working on with the save button. \n\nAll the outputs of your code will appear in the text box on the right.")
        msgBox.setWindowTitle("Online Help")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            print('OK clicked')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.showMaximized()
    sys.exit(app.exec_())