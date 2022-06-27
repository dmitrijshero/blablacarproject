import botrequests.dialogs as dialogs

script = [dialogs.location_stage,
          dialogs.checkin_stage,
          dialogs.checkout_stage,
          dialogs.hotel_number_stage,
          dialogs.hotel_photoes_stage,
          dialogs.final_stage]

stages = dialogs.Stages('highprice', script, search_method='PRICE_HIGHEST_FIRST')
