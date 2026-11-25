# Orbi

Robô de automação do Domínio Escrita Fiscal (uso interno da Conaud). Roda no computador,
sem IA e sem gastar tokens.

## Usar
1. Faça o login no Domínio Web e abra o Escrita Fiscal (feche as janelas filhas).
2. Abra o **Orbi.exe**, escolha a rotina, cole os códigos das empresas e clique em **Iniciar**.
3. Comece com **Simular** marcado; o Orbi vai até o diálogo de geração e cancela.
4. Não mexa no mouse durante a execução. Emergência: mouse no canto superior esquerdo.

Logs, relatórios e imagens das paradas ficam em `%APPDATA%\Orbi\logs`.
Ajustes da calibração ficam em `%APPDATA%\Orbi\config.json` (atualizações não apagam).

## Rotinas
| Rotina | Regra |
|---|---|
| Gerar parcelas — Saídas | 1 parcela, 1 dia, vencimento "Informar" |
| Gerar parcelas — Serviços | 1 parcela, 1 dia, vencimento "Informar" |

## Acrescentar uma função
1. Criar `orbi/rotinas/<nome>.py` com uma classe que herde de `Rotina` (ver `parcelas.py`).
2. Registrar em `orbi/rotinas/__init__.py` (lista `ROTINAS`).
3. Subir a versão em `orbi/__init__.py` (`VERSAO`) e enviar ao GitHub (ramo main).
   O GitHub monta o `Orbi.exe` e publica; o Orbi instalado se atualiza ao abrir.

## Segurança das rotinas
Toda etapa é conferida lendo a tela (OCR do Windows). Se algo não bater com o esperado,
a rotina **para**, salva a tela e mostra o motivo — nunca contorna, nunca gera duas vezes.
