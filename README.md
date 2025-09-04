# Controle_Atividades_Web

    Sistema web para registro e gerenciamento de atividades diárias de colaboradores, com controle de acesso por perfis e deploy na nuvem.

Este projeto foi desenvolvido como uma solução completa para equipes que precisam de uma ferramenta centralizada para monitorar e registrar tarefas. Um colaborador pode registrar suas atividades diárias, enquanto um gestor pode visualizar o trabalho de toda a sua equipe. Administradores têm controle total sobre o sistema, podendo gerenciar usuários, setores e tipos de atividades.

✨ Funcionalidades

    🔑 Autenticação de Usuários: Sistema completo de login, logout e controle de sessão.

    👤 Controle de Acesso por Nível:

        Colaborador: Registra e visualiza apenas suas próprias atividades.

        Gestor: Visualiza as atividades de todos os colaboradores do seu setor.

        Administrador: Acesso total ao sistema e aos painéis de gerenciamento.

    📜 Histórico Completo: Uma visão geral de todas as atividades com paginação para lidar com grandes volumes de dados.

    🔍 Filtragem Avançada: Filtre o histórico por data, colaborador, setor, tipo de atendimento ou por palavras-chave na descrição.

    ⚙️ Ações em Massa: Selecione múltiplas atividades no histórico para exclusão de uma só vez.

    📄 Detalhes e Edição: Visualize detalhes de uma atividade em um modal dinâmico ou edite registros individualmente.

    🔐 Gerenciamento de Perfil: O usuário pode visualizar seu perfil e alterar sua senha de forma segura.

    🛠️ Painel de Administração:

        Gerenciamento de Usuários (criar, editar perfis, status, etc.).

        Gerenciamento de Setores e associação de gestores.

        Gerenciamento de Tipos de Atividades.

🛠️ Tecnologias Utilizadas

    Backend: Python 3, Flask

    Banco de Dados: MySQL

    Frontend: HTML, CSS, JavaScript

    Bibliotecas Python:

        mysql-connector-python para conexão com o banco.

        bcrypt para hashing de senhas.

        python-dotenv para gerenciamento de variáveis de ambiente.

        gunicorn como servidor WSGI para produção.
