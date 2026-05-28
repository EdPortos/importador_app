BEGIN TRY
    BEGIN TRANSACTION;

    -- Limpa ou faz qualquer coisa coisa previa.
    DELETE FROM [DIRETORIA_CX].[HUB_ESTRUTURANTE].[DIM_CR];

    -- Carga
    INSERT INTO [DIRETORIA_CX].[HUB_ESTRUTURANTE].[DIM_CR] (
        [CR_FuncionarioRM],
        [NOME_CR],
        [CLIENTE],
        [CONTRATO],
        [INDUSTRIAS],
        [NUCLEO],
        [DIRETOR],
        [HEAD_QUALIDADE],
        [GERENTE_QUALIDADE],
        [DATA_CARGA]
    )
    SELECT
        [CR_FuncionarioRM],
        [NOME_CR],
        [CLIENTE],
        [CONTRATO],
        [INDUSTRIAS],
        [NÚCLEO],
        [DIRETOR],
        [HEAD_QUALIDADE],
        [GERENTE_QUALIDADE],
        [dt_carga]
    FROM [DIRETORIA_CX].[HUB_ESTRUTURANTE].[DIM_CR_COMPLETA]
    WHERE [is_current] = 1;

    --Finaliza a operação se não encontrar erros (muito, muito, muito seguro)
    COMMIT TRANSACTION;

END TRY
BEGIN CATCH
    -- Se houver qualquer erro no bloco TRY, desfaz o DELETE e libera a tabela
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    -- "print" do erro
    THROW;
END CATCH;