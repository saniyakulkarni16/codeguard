"""Step 1: turn source code into a normalized token stream.

Renaming variables, changing comments or reformatting must not change the stream:
  - comments / whitespace / newlines are dropped
  - identifiers  -> ID
  - numbers      -> NUM
  - strings      -> STR
  - keywords and operators are kept as they are
"""
import io
import keyword
import tokenize
from dataclasses import dataclass

_SKIP = {
    tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
    tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER,
}


@dataclass(frozen=True)
class Token:
    value: str  # normalized value
    line: int   # original line number (used later for highlighting)


def tokenize_source(source: str) -> list[Token]:
    tokens: list[Token] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type in _SKIP:
                continue
            kind = tokenize.tok_name.get(tok.type, "")
            if tok.type == tokenize.NAME:
                value = tok.string if keyword.iskeyword(tok.string) else "ID"
            elif tok.type == tokenize.NUMBER:
                value = "NUM"
            elif tok.type == tokenize.STRING or kind == "FSTRING_MIDDLE":
                value = "STR"
            else:
                value = tok.string
            tokens.append(Token(value, tok.start[0]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass  # keep whatever was tokenized before the error
    return tokens
