# Expectativa de rejeicao corrigida

Na pre-validacao, 12 testes produziram 1 falha: test_control_characters esperava
NONPORTABLE_ARCHIVE_NAME para nome com newline. O verificador herdado rejeita
esse arquivo antes, como INVALID_PACKAGE_STRUCTURE, pois newline quebra o
manifesto orientado a linhas. O teste foi corrigido para verificar a rejeicao
herdada especifica para newline; tabs e controles restantes continuam exigindo
NONPORTABLE_ARCHIVE_NAME. Nenhuma regra de aceitacao foi relaxada.
