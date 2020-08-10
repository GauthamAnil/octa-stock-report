import yaml
import sys
from collections import defaultdict
EMPTY = ' '

def load_yaml_file(file_name):
    with open(file_name,'r') as f:
        return yaml.load(f)

def split_transactions_by_scrip(transactions):
    res = {}
    for transaction in transactions:
        res.setdefault(transaction[2],[]).append(transaction)
    for scrip, l in res.items():
        l.sort(key=(lambda x: (x[1], x[3])))
    return res

def simulate_transactions(scrip_transactions, result, daily_aggregations, daily_scrip_aggregations):
    q = []
    for contract_no, ts, scrip, buy_sell, quantity, amount, stt in scrip_transactions:
        day = ts[:10]
        if buy_sell == 'BUY':
            buy_price = float(amount)/quantity
            q.append( (quantity, buy_price, day) )
            holding = sum(quantity1 for (quantity1,_,_) in q)
            result.append({ 'contract_no': contract_no, 
                            'transaction_date': ts,
                            'day': day,
                            'scrip': scrip,
                            'buy_sell': buy_sell,
                            'quantity': quantity,
                            'rate': buy_price,
                            'amount': amount,
                            'buy_amount': EMPTY,
                            'buy_rate': EMPTY,
                            'buy_date': EMPTY,
                            'transaction_type': EMPTY,
                            'profit_loss': EMPTY,
                            'holding': holding,
                            'stt': stt,
                             })
            daily_aggregations['daily_total'][day] -= amount
            #daily_scrip_aggregations['daily_delivery'][(day,scrip)] -= quantity * buy_price

        if buy_sell == 'SELL':
            total_sold_quantity = quantity
            sold_price = float(amount) / quantity
            assert total_sold_quantity > 0
            accumul_quantity = 0
            accumul_cost = 0.
            while accumul_quantity < total_sold_quantity:
                if len(q) == 0:
                    raise Exception("For scrip {scrip}, when trying to process sale at {ts}, we found you have sold more than you hold. Please correct your error.".format(**locals()))
                index_to_pop = 0
                for i in range(len(q)):
                    if q[i][2] == day:
                        index_to_pop = i
                        break
                bought_quantity, bought_price, buy_day = q.pop(index_to_pop)
                is_intra_day = buy_day == day
                resold_quantity = min(total_sold_quantity - accumul_quantity, bought_quantity)
                buy_amount = resold_quantity * bought_price
                accumul_quantity += resold_quantity
                accumul_cost += resold_quantity * bought_price
                if is_intra_day:
                    daily_scrip_aggregations['daily_intra_day'][(day,scrip)] += resold_quantity * (sold_price - bought_price)
                    #daily_scrip_aggregations['daily_delivery'][(day,scrip)] += resold_quantity * bought_price
                else:
                    daily_scrip_aggregations['daily_delivery'][(day,scrip)] += resold_quantity * (sold_price - bought_price)
                if resold_quantity < bought_quantity:
                    q.insert(index_to_pop, (bought_quantity - resold_quantity, bought_price, buy_day) )
                holding = sum(quantity1 for (quantity1,_,_) in q)
                result.append({ 'contract_no': contract_no, 
                                'transaction_date': ts,
                                'day': day,
                                'scrip': scrip,
                                'buy_sell': buy_sell,
                                'quantity': resold_quantity,
                                'rate': sold_price,
                                'amount': amount,
                                'buy_amount': "{:}".format(buy_amount),
                                'buy_rate': "{:}".format(bought_price),
                                'buy_date': buy_day,
                                'transaction_type': ('INTRA_DAY' if is_intra_day else 'DELIVERY'),
                                'profit_loss': resold_quantity * (sold_price - bought_price),
                                'holding': holding,
                                'stt': stt,
                            })
            average_cost = accumul_cost / accumul_quantity
            daily_aggregations['daily_total'][day] += amount
    return results

def compute_aggregates(daily_aggregations, daily_scrip_aggregations):
    for (day, scrip) in daily_scrip_aggregations['daily_intra_day']:
        daily_aggregations['daily_intra_day'][day] += daily_scrip_aggregations['daily_intra_day'][(day,scrip)]
    for (day, scrip) in daily_scrip_aggregations['daily_delivery']:
        daily_aggregations['daily_delivery'][day] += daily_scrip_aggregations['daily_delivery'][(day,scrip)]

def populate_aggregates(result, daily_aggregations, daily_scrip_aggregations):
    day_max_index = {}
    day_scrip_max_index = {}
    for i,result in enumerate(results):
        day_max_index[result['day']] = i
        day_scrip_max_index[(result['day'], result['scrip'])] = i
        
    for i, result in enumerate(results):
        day = result['day']
        scrip = result['scrip']
        k = (day, scrip)
        
        result['daily_total'] = daily_aggregations['daily_total'].get(day,EMPTY) if i == day_max_index[day] else EMPTY
        result['daily_intra_day'] = daily_aggregations['daily_intra_day'].get(day,EMPTY) if i == day_max_index[day] else EMPTY
        result['daily_delivery'] = daily_aggregations['daily_delivery'].get(day,EMPTY) if i == day_max_index[day] else EMPTY
        
        result['daily_scrip_intra_day'] = daily_scrip_aggregations['daily_intra_day'].get(k,EMPTY) if i == day_scrip_max_index[(day,scrip)] else EMPTY
        result['daily_scrip_delivery'] = daily_scrip_aggregations['daily_delivery'].get(k,EMPTY) if i == day_scrip_max_index[(day,scrip)] else EMPTY

header = 'contract_no,transaction_date,scrip,sell_or_buy,quantity,rate,amount,balance_quantity,sell_type,buy_date,buy_amount,buy_rate,PL,ac_daily_total,PL_intra_daily_transaction,PL_intra_daily_total,PL_delivery_transaction,PL_delivery_daily_total'
def format_result(result):
    return '{contract_no},{transaction_date},{scrip},{buy_sell},{quantity},{rate},{amount},{holding},{transaction_type},{buy_date},{buy_amount},{buy_rate},{profit_loss},{daily_total},{daily_scrip_intra_day},{daily_intra_day},{daily_scrip_delivery},{daily_delivery}'.format(**result)

if __name__ == '__main__':
    file_name = sys.argv[1]
    d = load_yaml_file(file_name)
    transactions_by_scrip = split_transactions_by_scrip(d['transactions'])
    results = []
    daily_aggregations = {
        'daily_total':defaultdict(float),
        'daily_intra_day':defaultdict(float),
        'daily_delivery':defaultdict(float),
    }
    daily_scrip_aggregations = {
        'daily_delivery':defaultdict(float),
        'daily_intra_day':defaultdict(float),
    }
    for scrip, scrip_transactions in sorted(transactions_by_scrip.items()):
        simulate_transactions(scrip_transactions, results, daily_aggregations, daily_scrip_aggregations )
    compute_aggregates(daily_aggregations, daily_scrip_aggregations)
    results.sort(key=(lambda x: (x['day'],x['scrip'],x['buy_sell'])))
    populate_aggregates(results, daily_aggregations, daily_scrip_aggregations)
    with open(file_name+".report.csv",'w') as f:
        print >> f, header
        for result in results:
            print >> f, format_result(result)
