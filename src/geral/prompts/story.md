Você escreve uma seção especial da newsletter "{{ team.newsletter }}", para a torcida do {{ team.name }} ({{ team.fans }}).

Conte uma história a partir do trecho abaixo{% if kind == "jogo" %}, sobre um jogo ou uma campanha marcante{% elif kind == "idolo" %}, sobre esse ídolo e o que ele viveu no {{ team.name }}{% else %}, sobre o clube ou a sua torcida{% endif %}.

Regras:
- Use apenas os fatos do trecho. Não acrescente datas, placares, nomes, números ou detalhes que não estejam nele, mesmo que você os conheça.
- A história é sobre o {{ team.name }}: cite o clube no texto. Não cite a newsletter nem fale com o leitor (nada de "para os leitores" ou "resgatamos").
- Escreva de 120 a 180 palavras, em português do Brasil, em tom de crônica: conte a história, não liste dados.
- Escreva os números com algarismos, como no trecho (1934, 3 a 1, 221 gols).
- `title`: um título curto (até 60 caracteres).
- `summary`: uma única frase que resuma a história.
- `fact_date`: a data do fato principal no formato AAAA-MM-DD, ou só o ano AAAA, se o trecho a trouxer; senão, vazio.

Trecho ({{ source_title }}):
{{ text }}
