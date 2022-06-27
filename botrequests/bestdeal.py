import botrequests.dialogs as dialogs

script = [dialogs.location_stage,
          dialogs.checkin_stage,
          dialogs.checkout_stage,
          dialogs.min_price_stage,
          dialogs.max_price_stage,
          dialogs.max_distance_stage,
          dialogs.hotel_number_stage,
          dialogs.hotel_photoes_stage,
          dialogs.final_stage]

stages = dialogs.Stages('bestdeal', script, search_method='DISTANCE_FROM_LANDMARK')
