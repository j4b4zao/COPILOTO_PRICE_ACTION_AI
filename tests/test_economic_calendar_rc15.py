"""Testes offline da configuração segura Trading Economics RC15."""

from economic_context.trading_economics_config import TradingEconomicsConfig


SECRET = "cliente:segredo-super-secreto"


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_desativada_por_padrao_sem_credencial():
    config = TradingEconomicsConfig.from_environment({})
    assert not config.enabled
    assert not config.ready


def teste_habilitada_exige_credencial():
    raises(
        ValueError,
        lambda: TradingEconomicsConfig.from_environment(
            {TradingEconomicsConfig.ENV_ENABLED: "true"}
        ),
    )


def teste_credencial_valida_fica_pronta():
    config = TradingEconomicsConfig.from_environment(
        {
            TradingEconomicsConfig.ENV_ENABLED: "1",
            TradingEconomicsConfig.ENV_API_KEY: SECRET,
        }
    )
    assert config.ready
    assert config.authorization_value() == SECRET


def teste_representacao_nao_expoe_credencial():
    config = TradingEconomicsConfig(api_key=SECRET)
    assert SECRET not in repr(config)
    assert "<redacted>" in repr(config)


def teste_diagnostico_nao_expoe_credencial():
    config = TradingEconomicsConfig(api_key=SECRET, enabled=True)
    diagnostics = config.diagnostics()
    assert SECRET not in str(diagnostics)
    assert diagnostics["credential_present"]
    assert diagnostics["observational_only"]
    assert not diagnostics["score_influence_allowed"]
    assert not diagnostics["order_execution_allowed"]


def teste_credencial_nao_pode_ir_na_url():
    raises(
        ValueError,
        lambda: TradingEconomicsConfig(
            api_key=SECRET,
            base_url="https://cliente:senha@api.tradingeconomics.com",
        ),
    )


def teste_base_url_exige_https():
    raises(
        ValueError,
        lambda: TradingEconomicsConfig(
            api_key=SECRET,
            base_url="http://api.tradingeconomics.com",
        ),
    )


def teste_base_url_rejeita_query_e_fragmento():
    raises(
        ValueError,
        lambda: TradingEconomicsConfig(
            api_key=SECRET,
            base_url="https://api.tradingeconomics.com?key=vaza",
        ),
    )
    raises(
        ValueError,
        lambda: TradingEconomicsConfig(
            api_key=SECRET,
            base_url="https://api.tradingeconomics.com#segredo",
        ),
    )


def teste_timeout_fica_limitado():
    raises(
        ValueError,
        lambda: TradingEconomicsConfig(api_key=SECRET, timeout_seconds=0),
    )
    raises(
        ValueError,
        lambda: TradingEconomicsConfig(api_key=SECRET, timeout_seconds=31),
    )


def teste_flag_invalida_falha_fechada():
    raises(
        ValueError,
        lambda: TradingEconomicsConfig.from_environment(
            {TradingEconomicsConfig.ENV_ENABLED: "talvez"}
        ),
    )


def teste_autorizacao_bloqueada_quando_desativada():
    config = TradingEconomicsConfig(api_key=SECRET, enabled=False)
    raises(PermissionError, config.authorization_value)


def teste_credencial_com_espaco_e_rejeitada():
    raises(
        ValueError,
        lambda: TradingEconomicsConfig(api_key="chave com espaco"),
    )


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC15 APROVADO")


if __name__ == "__main__":
    main()
