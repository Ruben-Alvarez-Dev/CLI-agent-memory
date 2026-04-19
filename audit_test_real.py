import asyncio
from pathlib import Path
from CLI_agent_memory.domain.loop import LoopEngine
from CLI_agent_memory.domain.types import Message, LLMResponse, ContextPack, AgentState
from CLI_agent_memory.config import LoopConfig

# Mock de Workspace real para la prueba
class RealFilesystemWorkspace:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
    def create(self, branch): return self.base_path
    def list_files(self, path): return []
    def write_file(self, path, file_path, content):
        p = path / file_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        print(f"  [SISTEMA REAL] Archivo escrito: {p}")

async def test_real_writing():
    # Simulamos una respuesta de LLM que "dice" que escribe un archivo
    llm_text = """
    Claro, acá tenés el código solicitado:
    
    **File: hola_mundo.py**
    ```python
    print("Hola desde el código REAL de producción!")
    ```
    
    ¡Listo!
    """
    
    # Creamos el motor de producción real
    class MockLLM:
        async def generate(self, *args, **kwargs):
            return LLMResponse(text=llm_text, files_edited=1)
        def is_available(self): return True

    tmp_dir = Path("/tmp/audit_test_real")
    ws = RealFilesystemWorkspace(tmp_dir)
    engine = LoopEngine(llm=MockLLM(), memory=None, thinking=None, workspace=ws, vault=None, config=LoopConfig())
    
    # Invocamos la lógica de _code que acabo de arreglar
    history = [Message(role="system", content="sys")]
    from CLI_agent_memory.domain.state import TaskContext
    ctx = TaskContext(tmp_dir)
    ctx.iteration = 1
    ctx.plan = "test"
    
    print("Ejecutando LoopEngine._code real...")
    await engine._code(ctx, history)
    
    # Verificamos si el archivo existe en el disco REAL
    test_file = tmp_dir / "hola_mundo.py"
    if test_file.exists():
        print(f"\n✅ PRUEBA SUPERADA: El archivo '{test_file}' existe y su contenido es:")
        print(f"--- CONTENT ---\n{test_file.read_text()}---------------")
    else:
        print("\n❌ FALLO: El archivo no se creó.")

if __name__ == "__main__":
    asyncio.run(test_real_writing())
