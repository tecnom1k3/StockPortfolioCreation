import requests as http
import pandas as pd
import json
import keys

file_name = 'pickedStocks.json'
api_key = keys.financialmodelingprep_api_key


def save_stocks(stocks, target_file_name):
    with open(target_file_name, 'w') as outfile:
        json.dump(stocks, outfile)

    print('Saved')


def retrieve_picked_stocks_from_file(picked_stocks_file_name):
    with open(picked_stocks_file_name) as json_file:
        data = json.load(json_file)
        return data


def get_stocks():
    params = {
        'apikey': api_key
    }

    stocks = http.get('https://financialmodelingprep.com/api/v3/stock/list', params)
    return stocks.json()


def pick_stocks(all_stocks):
    params = {
        'apikey': api_key
    }

    picked_stocks = []
    for stock in all_stocks:
        # ! check if keys exist
        if 'name' not in stock or 'symbol' not in stock:
            continue

        # ? ignore foreign companies (American Deposit Receipts)
        # ? ignore foreign companies (contains '.' in name)
        if 'ADR' in stock['name'] or '.' in stock['symbol']:
            continue

        symbol = stock['symbol']

        financial_ratios = http.get(f'https://financialmodelingprep.com/api/v3/ratios/{symbol}', params)
        financial_ratios = financial_ratios.json()
        if len(financial_ratios) <= 0:
            continue
        financial_ratios = financial_ratios[0]  # the service returns ratios per year, this gets latest

        # ! check if keys exist
        if 'returnOnAssets' not in financial_ratios or 'priceEarningsRatio' not in financial_ratios:
            continue

        roa = financial_ratios['returnOnAssets']
        pe_ratio = financial_ratios['priceEarningsRatio']

        if roa is None or pe_ratio is None:
            continue

        print(f'{symbol}: roa={roa}, p-e ratio={pe_ratio}')

        # TODO: Ignore utilities and financial stocks (mutual funds, banks and insurance companies)
        # TODO: I believe funds are already ignored because pe_ratio would be None
        # TODO: But still some utilities and financial stocks may remain

        # return on assets must be at least 25%
        # price to earnings ratio of 5 or less may indicate that the year's data is unusual in some way
        if roa >= 0.25 and pe_ratio > 5:
            picked_stocks.append({
                'symbol': symbol,
                'name': stock['name'],
                'roa': roa,
                'pe_ratio': pe_ratio
            })

    print('Picked')
    return picked_stocks


def pick_new_stocks():
    stocks = get_stocks()
    picked_stocks = pick_stocks(stocks)
    save_stocks(picked_stocks, file_name)


def evaluate_picked_stocks():
    picked_stocks = retrieve_picked_stocks_from_file(file_name)
    picked_df = pd.DataFrame(picked_stocks)

    # sort by roa to assign first ranking (according to page 56 of TLB that STILL beats the market)
    picked_df.sort_values(by=['roa'], ascending=False, inplace=True)
    picked_df['roa_ranking'] = [i + 1 for i in range(len(picked_stocks))]
    # sort by pe ratio to assign second ranking (according to page 57 of TLB that STILL beats the market)
    picked_df.sort_values(by=['pe_ratio'], ascending=False, inplace=True)
    picked_df['pe_ranking'] = [i + 1 for i in range(len(picked_stocks))]
    # calculate overall ranking
    picked_df['overall_ranking'] = picked_df['pe_ranking'] + picked_df['roa_ranking']
    picked_df.sort_values(by=['overall_ranking'], ascending=True, inplace=True)

    for i, stock in picked_df.iterrows():
        picked_df.at[i, 'industry'] = get_company_industry(stock)

    picked_df.to_excel('best_picks.xlsx')


def get_company_industry(stock):
    params = {
        'apikey': api_key
    }

    symbol = stock['symbol']
    company_profile = http.get(f'https://financialmodelingprep.com/api/v3/profile/{symbol}', params)
    company_profile = company_profile.json()
    if len(company_profile) <= 0:
        return ''
    return company_profile[0]['industry']


if __name__ == "__main__":
    # pick_new_stocks()

    # once gone through the picking, making a ton of requests to the API
    # we can evaluate the stocks saved to the txt file:
    evaluate_picked_stocks()
