; Functions
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @function))

; Types
(type_identifier) @type
(primitive_type) @type

; Strings
(string_literal) @string

; Numbers
(number_literal) @number

; Comments
(comment) @comment