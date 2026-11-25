from dataclasses import dataclass


@dataclass
class Resultado:
    empresa: str
    texto: str
    ok: bool = True


class Rotina:
    id = ""
    nome = ""
    descricao = ""
    pede_empresas = True          # mostra o campo de códigos de empresa
    precisa_regioes = ()          # regiões que precisam estar calibradas para rodar de verdade

    def executar_empresa(self, t, codigo, simular):
        """Executa a rotina para uma empresa e devolve o texto do resultado.
        Para parar com segurança, levante tela.Parar("motivo")."""
        raise NotImplementedError
