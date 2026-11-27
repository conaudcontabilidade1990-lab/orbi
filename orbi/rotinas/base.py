from dataclasses import dataclass


@dataclass
class Resultado:
    empresa: str
    texto: str
    ok: bool = True


class Rotina:
    id = ""
    nome = ""
    departamento = "fiscal"       # id do departamento no Portal Conaud (conta.DEPARTAMENTOS)
    descricao = ""
    pede_empresas = True          # mostra o campo de códigos de empresa
    precisa_regioes = ()          # regiões que precisam estar calibradas para rodar de verdade
    usa_competencia = False       # mostra "competência de/até" na tela; vem em self.competencia
    competencia = None            # ((ano, mês) inicial, (ano, mês) final) quando usa_competencia
    usa_dominio = True            # False: não mexe na tela (não minimiza o Orbi nem espera o Domínio)
    usa_pasta_xml = False
    usa_periodo = False           # mostra "Período (dias)" de/até; vem em self.periodo (date, date) ou None         # mostra "Pasta dos XML" na tela; vem em self.pasta_base

    def executar_empresa(self, t, codigo, simular):
        """Executa a rotina para uma empresa e devolve o texto do resultado.
        Para parar com segurança, levante tela.Parar("motivo")."""
        raise NotImplementedError
