class AdaptiveEngine:


    def __init__(self):

        self.bonus = 0



    # =====================================
    # ANALISAR PERFORMANCE DO SETUP
    # =====================================

    def analisar_setup(

        self,

        setup,

        setup_tracker

    ):


        self.bonus = 0



        if setup is None:

            return 0



        nome = setup.get(

            "setup"

        )



        dados = setup_tracker.calcular()



        if nome not in dados:


            return 0




        win_rate = dados[nome]["win_rate"]




        # =================================
        # AJUSTE POSITIVO
        # =================================


        if win_rate >= 70:


            self.bonus = 15



        elif win_rate >= 60:


            self.bonus = 8




        # =================================
        # AJUSTE NEGATIVO
        # =================================


        elif win_rate <= 40:


            self.bonus = -15



        elif win_rate <= 50:


            self.bonus = -8




        return self.bonus





    # =====================================
    # APLICAR AO SCORE
    # =====================================

    def ajustar_score(

        self,

        score,

        bonus

    ):


        novo_score = score + bonus



        if novo_score > 100:


            novo_score = 100



        if novo_score < 0:


            novo_score = 0



        return novo_score