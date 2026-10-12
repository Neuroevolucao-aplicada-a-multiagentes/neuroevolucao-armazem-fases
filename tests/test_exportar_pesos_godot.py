import os
import sys
from types import SimpleNamespace

import numpy as np

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_RAIZ, "src"))

from exportar_pesos_godot import ErroExportacao, buscar_genoma, genoma_para_godot
from rede_transfer import RedeNeural
from treinar import _genome_json

_NPZ = os.path.join(_RAIZ, "melhor_rede_fase5.npz")
_CHAVES = ("w1", "w2", "w3", "b1", "b2", "b3")


class _Consulta:
    """Imita o encadeamento select/eq/order/limit/execute do cliente Supabase."""

    def __init__(self, linhas):
        self._linhas = list(linhas)

    def select(self, *_):
        return self

    def eq(self, coluna, valor):
        return _Consulta(l for l in self._linhas if l.get(coluna) == valor)

    def order(self, coluna, desc=False):
        return _Consulta(sorted(self._linhas, key=lambda l: l.get(coluna) or "", reverse=desc))

    def limit(self, n):
        return _Consulta(self._linhas[:n])

    def execute(self):
        return SimpleNamespace(data=self._linhas)


class _BancoFalso:
    def __init__(self, tabelas):
        self._tabelas = tabelas

    def schema(self, _):
        return self

    def table(self, nome):
        return _Consulta(self._tabelas.get(nome, []))


def _genoma_da_fase5():
    rede = RedeNeural()
    rede.carregar(_NPZ)
    return _genome_json(SimpleNamespace(brain=rede))


def _banco_com_runs():
    genoma = _genoma_da_fase5()
    return _BancoFalso({
        "run": [
            {"id": "r-antiga", "phase_code": "fase_5", "status": "completed",
             "started_at": "2026-05-23T15:08", "run_label": "antiga"},
            {"id": "r-nova", "phase_code": "fase_5", "status": "completed",
             "started_at": "2026-06-01T10:00", "run_label": "nova"},
            {"id": "r-falhou", "phase_code": "fase_5", "status": "failed",
             "started_at": "2026-07-01T10:00", "run_label": "falhou"},
            {"id": "r-outra", "phase_code": "fase_4_2", "status": "completed",
             "started_at": "2026-08-01T10:00", "run_label": "outra fase"},
        ],
        "checkpoint": [
            {"id": "c-nova", "run_id": "r-nova", "checkpoint_type": "best",
             "fitness": 9.0, "individual_id": "i-nova"},
            {"id": "c-antiga", "run_id": "r-antiga", "checkpoint_type": "best",
             "fitness": 5.0, "individual_id": "i-antiga"},
        ],
        "individual": [
            {"id": "i-nova", "genome": genoma, "fitness": 9.0},
            {"id": "i-antiga", "genome": None, "fitness": 5.0},
        ],
    })


def test_conversao_reproduz_o_checkpoint_exatamente():
    rede = genoma_para_godot(_genoma_da_fase5(), origem={})
    local = np.load(_NPZ)
    assert rede["meta"] == [16, 32, 16, 2]
    for k in _CHAVES:
        assert np.array_equal(np.asarray(rede[k]), local[k]), f"{k} divergiu"


def test_busca_usa_a_run_concluida_mais_recente_da_fase():
    genoma, origem = buscar_genoma(_banco_com_runs(), fase="5")
    assert origem["run_id"] == "r-nova"
    assert origem["checkpoint_id"] == "c-nova"
    assert origem["individual_id"] == "i-nova"
    assert origem["fase"] == "fase_5"
    assert genoma is not None


def test_busca_aceita_fase_com_ponto_ou_sublinhado():
    for fase in ("4_2", "4.2"):
        try:
            buscar_genoma(_banco_com_runs(), fase=fase)
        except ErroExportacao as e:
            assert "checkpoint best" in str(e), f"{fase}: {e}"
        else:
            raise AssertionError("a fase_4_2 do banco falso nao tem checkpoint")


def test_busca_falha_quando_o_individuo_nao_tem_genoma():
    try:
        buscar_genoma(_banco_com_runs(), run_id="r-antiga")
    except ErroExportacao as e:
        assert "sem genoma" in str(e)
    else:
        raise AssertionError("deveria falhar sem genoma")


def test_busca_falha_sem_run_concluida():
    banco = _BancoFalso({"run": [
        {"id": "x", "phase_code": "fase_3", "status": "failed", "started_at": "2026-01-01"}]})
    try:
        buscar_genoma(banco, fase="3")
    except ErroExportacao as e:
        assert "nenhuma run concluida" in str(e) and "failed" in str(e)
    else:
        raise AssertionError("deveria falhar sem run concluida")


def test_rejeita_rede_fora_do_contrato():
    genoma = _genoma_da_fase5()
    genoma["meta"]["input_size"] = 15
    genoma["w1"] = genoma["w1"][:15]
    try:
        genoma_para_godot(genoma, origem={})
    except ErroExportacao as e:
        assert "contrato" in str(e)
    else:
        raise AssertionError("deveria rejeitar 15 entradas")


def test_rejeita_forma_inconsistente_com_a_meta():
    genoma = _genoma_da_fase5()
    genoma["w2"] = [linha[:10] for linha in genoma["w2"]]
    try:
        genoma_para_godot(genoma, origem={})
    except ErroExportacao as e:
        assert "w2" in str(e)
    else:
        raise AssertionError("deveria rejeitar w2 com forma errada")


def test_rejeita_pesos_nao_finitos():
    genoma = _genoma_da_fase5()
    genoma["b1"][0] = float("nan")
    try:
        genoma_para_godot(genoma, origem={})
    except ErroExportacao as e:
        assert "NaN" in str(e)
    else:
        raise AssertionError("deveria rejeitar NaN")


if __name__ == "__main__":
    test_conversao_reproduz_o_checkpoint_exatamente()
    test_busca_usa_a_run_concluida_mais_recente_da_fase()
    test_busca_aceita_fase_com_ponto_ou_sublinhado()
    test_busca_falha_quando_o_individuo_nao_tem_genoma()
    test_busca_falha_sem_run_concluida()
    test_rejeita_rede_fora_do_contrato()
    test_rejeita_forma_inconsistente_com_a_meta()
    test_rejeita_pesos_nao_finitos()
    print("OK")
