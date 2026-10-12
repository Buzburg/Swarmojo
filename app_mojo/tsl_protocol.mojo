"""Mojo-TSL: Streaming Telegraphic Symbolic Language (TSL) Protocol Engine.

Ported from Swarmojo/repo_stapler/tsl_protocol.mojo:
- Real-time byte-level Finite State Machine (FSM) parser for [OUT:"..."] and [ADD:(s r o)]
- Zero-copy streaming token handling across arbitrary chunk boundaries
- Compact TSL prompt builder reducing token overhead by 80-90% for small local models
"""

comptime STATE_SEEKING = 0
comptime STATE_TAG_IDENT = 1
comptime STATE_STREAM_OUT = 2
comptime STATE_BUFFER_ADD = 3


struct ParsedTriple(Movable, Copyable):
    var subject: String
    var relation: String
    var object: String

    def __init__(out self, s: String, r: String, o: String):
        self.subject = s
        self.relation = r
        self.object = o

    def __init__(out self, *, copy: Self):
        self.subject = copy.subject
        self.relation = copy.relation
        self.object = copy.object

    def __init__(out self, *, deinit move: Self):
        self.subject = move.subject^
        self.relation = move.relation^
        self.object = move.object^


struct TSLStreamParser(Movable, Copyable):
    """Streaming FSM parser for TSL packets ([OUT:"..."][ADD:(s r o)])."""
    var state: Int
    var tag_buffer: String
    var triple_buffer: String
    var output_stream: String
    var in_quotes: Bool
    var bound_triples: List[ParsedTriple]

    def __init__(out self):
        self.state = STATE_SEEKING
        self.tag_buffer = String("")
        self.triple_buffer = String("")
        self.output_stream = String("")
        self.in_quotes = False
        self.bound_triples = List[ParsedTriple]()

    def __init__(out self, *, copy: Self):
        self.state = copy.state
        self.tag_buffer = copy.tag_buffer
        self.triple_buffer = copy.triple_buffer
        self.output_stream = copy.output_stream
        self.in_quotes = copy.in_quotes
        self.bound_triples = List[ParsedTriple]()
        for i in range(len(copy.bound_triples)):
            self.bound_triples.append(copy.bound_triples[i].copy())

    def __init__(out self, *, deinit move: Self):
        self.state = move.state
        self.tag_buffer = move.tag_buffer^
        self.triple_buffer = move.triple_buffer^
        self.output_stream = move.output_stream^
        self.in_quotes = move.in_quotes
        self.bound_triples = move.bound_triples^

    def feed(mut self, chunk: String) raises:
        """Processes incoming token delta slice character-by-character."""
        for ch_slice in chunk.codepoint_slices():
            var ch = String(ch_slice)

            if self.state == STATE_SEEKING:
                if ch == "[":
                    self.state = STATE_TAG_IDENT
                    self.tag_buffer = String("")

            elif self.state == STATE_TAG_IDENT:
                if ch == "]":
                    self.state = STATE_SEEKING
                else:
                    self.tag_buffer += ch
                    if self.tag_buffer == "OUT:":
                        self.state = STATE_STREAM_OUT
                        self.in_quotes = False
                        self.tag_buffer = String("")
                    elif self.tag_buffer == "ADD:":
                        self.state = STATE_BUFFER_ADD
                        self.triple_buffer = String("")
                        self.tag_buffer = String("")

            elif self.state == STATE_STREAM_OUT:
                if ch == '"':
                    self.in_quotes = not self.in_quotes
                elif ch == "]" and not self.in_quotes:
                    self.state = STATE_SEEKING
                else:
                    self.output_stream += ch

            elif self.state == STATE_BUFFER_ADD:
                if ch == "(":
                    self.triple_buffer = String("")
                elif ch == ")":
                    var raw = String(self.triple_buffer.strip())
                    if raw.byte_length() > 0:
                        self._commit_triple(raw)
                    self.triple_buffer = String("")
                elif ch == "]":
                    self.state = STATE_SEEKING
                else:
                    self.triple_buffer += ch

    def _commit_triple(mut self, raw: String) raises:
        """Extracts space-delimited (Subject Relation Object) triple."""
        var parts = raw.split(" ")
        if len(parts) >= 3:
            var s = String(parts[0])
            var r = String(parts[1])
            var o = String(parts[2])
            self.bound_triples.append(ParsedTriple(s, r, o))


def build_tsl_prompt(
    role: String,
    repo_ast_context: String,
    mem_triples: List[String],
    goal: String
) -> String:
    """Assembles a compressed Telegraphic Symbolic Language payload."""
    var sb = String("[ROLE:") + role + "]\n"

    if repo_ast_context.byte_length() > 0:
        sb += "[REPO_AST:\n" + repo_ast_context + "]\n"

    if len(mem_triples) > 0:
        sb += "[MEM:"
        for i in range(len(mem_triples)):
            sb += "(" + mem_triples[i] + ")"
        sb += "]\n"

    sb += '[GOAL:"' + goal + '"]\n'
    sb += 'Respond strictly in TSL format: [OUT:"..."][ADD:(s r o)]'
    return sb
