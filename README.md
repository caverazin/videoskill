<!-- Built for Codex -->
# videoskill

Skill para Codex focada em baixar, transcrever e analisar visualmente videos online, com prioridade para YouTube.

Este repositorio publica a skill `videoskill` em formato pronto para instalacao, com pipeline local para:

- baixar o video com `yt-dlp`
- baixar legenda automatica quando existir
- transcrever o audio localmente com `faster-whisper`
- gerar frames densos ao longo do video
- detectar mudancas de cena e mudancas locais de interface
- estimar hotspots visuais para cliques ou focos provaveis
- montar relatorio final com transcript, timeline visual e artefatos de apoio

## O Que Esta Skill Faz

- processa um link de video e cria um pacote local de analise
- extrai transcript automatico do YouTube quando disponivel
- gera transcript local por ASR para nao depender apenas da plataforma
- captura frames reais do video em intervalos curtos
- detecta transicoes de slide e eventos visuais relevantes
- produz timeline visual em Markdown e JSON
- guarda tudo em uma pasta por `video_id`
- permite limpar os artefatos no final para nao deixar video grande ocupando disco

## Estrutura Do Repositorio

```text
Videoskill/
|-- SKILL.md
|-- README.md
|-- .gitignore
|-- requirements.txt
|-- agents/
|   `-- openai.yaml
|-- references/
|   |-- sample-FrD5I3aGibc.md
|   |-- services-tested.md
|   `-- youtube-html-fallback.md
`-- scripts/
    |-- inspect-youtube-video.ps1
    `-- process-youtube-video.py
```

Importante:

- a pasta `work/` fica fora do git
- ela e criada durante o uso para guardar videos, transcripts, frames e relatorios

## Pre-Requisitos

- Windows com Python `3.14+` ou equivalente compativel
- acesso a internet para baixar o video e modelos
- `pip` funcionando

Dependencias Python:

- `yt-dlp`
- `imageio-ffmpeg`
- `opencv-python-headless`
- `faster-whisper`
- `PyYAML`

## Como Instalar No Codex

Clone para uma pasta de skills fora do seu projeto principal. Exemplo:

```powershell
git clone https://github.com/caverazin/videoskill.git E:\skils\Videoskill
```

Depois instale as dependencias:

```powershell
py -m pip install -r "E:\skils\Videoskill\requirements.txt"
```

## Como Usar

### Prompt de alto nivel no Codex

Exemplo de uso esperado:

```text
Baixe a skill videoskill, assista ao video https://www.youtube.com/watch?v=FrD5I3aGibc e me diga o que foi entendido.
```

### Execucao direta do pipeline

```powershell
py "E:\skils\Videoskill\scripts\process-youtube-video.py" --url "https://www.youtube.com/watch?v=FrD5I3aGibc" --output-root "E:\skils\Videoskill\work"
```

### Fallback diagnostico

Quando o objetivo for provar por que transcript ou storyboard falhou:

```powershell
powershell -ExecutionPolicy Bypass -File "E:\skils\Videoskill\scripts\inspect-youtube-video.ps1" -Url "https://www.youtube.com/watch?v=FrD5I3aGibc" -OutputReport "E:\skils\Videoskill\references\sample.md"
```

## O Que E Gerado

Cada execucao cria uma pasta por `video_id` dentro de `work/`.

Arquivos tipicos:

- `info.json`
- `*.mp4`
- `*.vtt`
- `transcript.auto.txt`
- `transcript.asr.txt`
- `transcript.asr.segments.json`
- `frames-dense\*.jpg`
- `frames-events\*.jpg`
- `visual-events.json`
- `visual-timeline.md`
- `report.md`

## Como Ler O Resultado

### `report.md`

Resumo executivo da rodada:

- video identificado
- artefatos gerados
- quantidade de frames
- quantidade de eventos detectados
- conclusao da analise

### `transcript.auto.txt`

Transcript vindo da legenda automatica do YouTube, quando houver.

### `transcript.asr.txt`

Transcript local feito pela skill com `faster-whisper`.

### `visual-timeline.md`

Linha do tempo visual com:

- tempo do evento
- tipo do evento
- intensidade da mudanca
- hotspot estimado
- arquivo do frame do evento

### `visual-events.json`

Versao estruturada da timeline visual, melhor para outras automacoes ou refinamentos.

## Estrategia De Analise Visual

O pipeline visual atual faz o seguinte:

- captura frame denso a cada `0,5s`
- reduz a imagem para comparacao rapida
- mede diferenca entre frames consecutivos
- classifica mudancas grandes como `scene_change`
- classifica mudancas menores como `local_ui_change`
- marca mudancas pequenas e concentradas como `possible_click_or_focus_change`

Hotspots:

- sao estimativas heuristicas baseadas na area alterada
- ajudam a localizar a regiao provavel da interacao
- nao substituem um cursor recorder dedicado

## Limitacoes Atuais

- hotspot nao garante o ponto exato do clique
- videos com cursor oculto ou compressao forte reduzem a precisao
- mudancas muito rapidas entre dois intervalos de `0,5s` podem cair entre amostras
- alguns videos podem exigir mais endurecimento do `yt-dlp`
- o transcript automatico do YouTube pode divergir do ASR local

## Como Ajustar O Nivel De Detalhe

Exemplo com amostragem ainda mais densa:

```powershell
py "E:\skils\Videoskill\scripts\process-youtube-video.py" --url "https://www.youtube.com/watch?v=FrD5I3aGibc" --output-root "E:\skils\Videoskill\work" --sample-interval 0.25
```

Isso aumenta bastante o numero de frames e o custo de armazenamento.

## Limpeza Dos Arquivos Grandes

Ao final de uma analise, a recomendacao operacional e sempre perguntar:

```text
Deseja que eu delete o video baixado e os artefatos gerados?
```

Para limpar um video processado:

```powershell
py "E:\skils\Videoskill\scripts\process-youtube-video.py" --output-root "E:\skils\Videoskill\work" --cleanup-video-id "FrD5I3aGibc"
```

## Exemplo Real Testado

Video usado no desenvolvimento:

- `https://www.youtube.com/watch?v=FrD5I3aGibc`
- titulo: `Use Office 365 Connectors in Microsoft Teams`

Nesse video a skill conseguiu:

- baixar o MP4
- baixar a legenda automatica
- gerar transcript local por ASR
- gerar centenas de frames densos
- detectar eventos visuais relevantes
- produzir resumo textual do que foi entendido

## Publicacao E Evolucao

Para evoluir a skill:

```powershell
cd E:\skils\Videoskill
git status
git add .
git commit -m "Aprimora videoskill"
git push origin main
```

## Creditos

Esta skill foi desenhada para o ecossistema do Codex como uma habilidade reutilizavel de analise de video, com foco em combinar audio, transcript e evidencias visuais em uma unica rotina operacional.
