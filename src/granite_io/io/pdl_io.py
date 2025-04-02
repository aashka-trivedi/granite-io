# Standard
import pathlib
from typing import Any, Callable

# Third Party
from pdl.pdl import exec_program, parse_file, parse_str
from pdl.pdl_ast import CallBlock, FunctionBlock, Program
import aconfig

# Local
from .base import ChatCompletionResults, InputOutputProcessor
from granite_io.types import ChatCompletionInputs


class PdlInputOutputProcessor(InputOutputProcessor):
    """
    Base class for input-output processors that work by executing a
    Prompt Declaration Language (PDL) function processing `ChatCompletionInputs`.
    """

    _pdl_function: FunctionBlock | None
    """PDL function used to process the input."""
    _pdl_scope: dict[str, Any] | None
    """Initial scope in which the PDL program is executed"""

    def __init__(
        self,
        config: aconfig.Config | None = None,
        pdl: FunctionBlock | str | None = None,
        pdl_file: str | None = None,
        pdl_scope: dict[str, Any] | None = None,
    ):
        """
        :param config: Setup config for this IO processor
        :param pdl: PDL function processing the `ChatCompletionInputs`
        :param pdl_file: Name of the PDL file containing the function processing the `ChatCompletionInputs`
        :param pdl_scope: Initial environment in which the function is executed
        """
        super().__init__(config)
        if isinstance(pdl, str):
            prog, _ = parse_str(pdl, file_name=pdl_file)
            self._pdl_function = prog.root
        elif pdl is None and pdl_file is not None:
            prog, _ = parse_file(pdl_file)
            self._pdl_function = prog.root
        else:
            self._pdl_function = pdl
        self._pdl_scope = pdl_scope

    def create_chat_completion(
        self, inputs: ChatCompletionInputs
    ) -> ChatCompletionResults:
        prog = Program(
            CallBlock(defs= {"_pdl_function": self._pdl_function},call="${_pdl_function}", args={"inputs": inputs.model_dump()})
        )
        results = exec_program(prog, scope=self._pdl_scope)
        return ChatCompletionResults.model_validate(results)


class MultiShotInputOutputProcessor(PdlInputOutputProcessor):
    """
    Input-output processor asking multiple answers until a predicate is satisfied.
    """

    def __init__(
        self,
        config: aconfig.Config | None = None,
        model: str | None = None,
        backend: str | None = None,
        max_iterations: int = 5,
        validator: Callable[[ChatCompletionResults], bool] | None = None,
    ):
        """
        :param config: Setup config for this IO processor
        :param model: Model name used by the backend.
        :param backend: Backend name.
        :param max_iterations: Maximal number of model calls.
        :param validator: predicate that the response must satisfy.
        """
        cwd = pathlib.Path(__file__).parent.resolve()
        super().__init__(
            config,
            pdl_file=cwd / "multi_shot.pdl",
            pdl_scope={
                "model": model,
                "backend": backend,
                "k": max_iterations,
                "validator": validator,
            },
        )
