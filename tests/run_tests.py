import sys
import traceback

sys.path.insert(0, "/home/claude/sismolab_avl")

import tests.test_servicio_eventos as t
import tests.test_gestor_asociaciones as t2

funciones = [getattr(t, nombre) for nombre in dir(t) if nombre.startswith("test_")]
funciones += [getattr(t2, nombre) for nombre in dir(t2) if nombre.startswith("test_")]
fallos = 0
for f in funciones:
    try:
        f()
        print(f"OK   {f.__name__}")
    except Exception:
        fallos += 1
        print(f"FAIL {f.__name__}")
        traceback.print_exc()

print(f"\n{len(funciones) - fallos}/{len(funciones)} pasaron")
sys.exit(1 if fallos else 0)