# JobPilot AI — candidatura assistida (LinkedIn e Gupy)

## Estado da integração

O botão **Candidatura assistida** está conectado ao companion local. Ele abre
um Chromium visível com perfil persistente, aceita o login feito manualmente,
abre o início da candidatura simplificada do LinkedIn ou o fluxo de candidatura
da Gupy, preenche somente os campos conhecidos (nome, e-mail, celular e LinkedIn) e
usa contato extraído do currículo quando o perfil salvo não tem o dado. Quando
uma pergunta de resumo/experiência ou competências corresponde a palavras-chave
da vaga presentes no currículo, sugere trechos literais do currículo. Campos
sem evidência continuam vazios. O fluxo para para revisão de campos variáveis.
O assistente **não envia
automaticamente** a candidatura nesta versão e não afirma que ela foi enviada.

O JobPilot também oferece busca de vagas por LinkedIn/Gupy (dependendo da
disponibilidade das fontes) e análise de palavras-chave comprovadas pelo currículo.
O score não representa pontuação real da Gupy, apenas uma heurística de comparação.

## Rodar no Linux

```bash
cd companion
npm install
npx playwright install chromium
npm test
npm start
```

Em outro terminal, inicialize a aplicação principal usando o Docker Compose
na raiz do repositório. Acesse http://localhost:3000, entre na conta do JobPilot,
envie um currículo PDF e vá em **Vagas**. Preencha os dados básicos do candidato
no painel (salvos em localStorage no computador), escolha LinkedIn ou Gupy,
busque oportunidades e clique em **Candidatura assistida**. A sessão do navegador
será persistida localmente em `.jobpilot-browser`, que não deve ser versionada.

**Limitações importantes**
- Não há extração automática de dados autenticados do LinkedIn. Isso contraria
  as regras da plataforma; os resultados vêm da fonte pública do JobPilot.
- Vagas do LinkedIn que redirecionem para outro domínio permanecem abertas para
  navegação manual. O companion não preenche páginas de terceiros.
- Não existe integração oficial de submissão direta à Gupy neste agente.
  Formulários variáveis, perguntas adicionais, login, anexos e confirmações
  precisam de validação específica antes de habilitar envio automático.
- O texto do currículo é carregado após o clique em **Candidatura assistida** e
  enviado ao companion local apenas para preencher campos daquela sessão. Ele
  não é salvo no perfil do navegador pelo companion.
- O PDF enviado ao backend atualmente tem texto extraído, mas não armazena
  de forma reutilizável os bytes do arquivo. Portanto, não é possível
  anexá-lo automaticamente em formulários do navegador nesta versão.
- O botão não altera o pipeline para "candidatado", porque o envio real
  ainda não é verificável. Nunca coloque senhas, CPF ou cookies no código.
- O companion usa localhost; não exponha a porta 8765 à rede externa.
