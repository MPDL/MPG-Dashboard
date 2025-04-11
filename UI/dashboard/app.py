from shiny.express import input, render, ui
from shared import publications, open_access_count, closed_access_count, not_findable_count
from pathlib import Path
from db import get_publications, get_oa_publications, extract_month_year
from collections import Counter





summe_publikationen = len(publications)
publications = []
oa_publications_list = []
ca_publications_list = []

# From https://icons.getbootstrap.com/icons/piggy-bank/

book = ui.HTML(
    """
        <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" fill="currentColor" class="bi bi-book" viewBox="0 0 16 16">
            <path d="M1 2.828c.885-.37 2.154-.769 3.388-.893 1.33-.134 2.458.063 3.112.752v9.746c-.935-.53-2.12-.603-3.213-.493-1.18.12-2.37.461-3.287.811zm7.5-.141c.654-.689 1.782-.886 3.112-.752 1.234.124 2.503.523 3.388.893v9.923c-.918-.35-2.107-.692-3.287-.81-1.094-.111-2.278-.039-3.213.492zM8 1.783C7.015.936 5.587.81 4.287.94c-1.514.153-3.042.672-3.994 1.105A.5.5 0 0 0 0 2.5v11a.5.5 0 0 0 .707.455c.882-.4 2.303-.881 3.68-1.02 1.409-.142 2.59.087 3.223.877a.5.5 0 0 0 .78 0c.633-.79 1.814-1.019 3.222-.877 1.378.139 2.8.62 3.681 1.02A.5.5 0 0 0 16 13.5v-11a.5.5 0 0 0-.293-.455c-.952-.433-2.48-.952-3.994-1.105C10.413.809 8.985.936 8 1.783"/>
        </svg>
    """
)

bookmark = ui.HTML(
    """
        <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" fill="currentColor" class="bi bi-bookmark-heart" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M8 4.41c1.387-1.425 4.854 1.07 0 4.277C3.146 5.48 6.613 2.986 8 4.412z"/>
            <path d="M2 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v13.5a.5.5 0 0 1-.777.416L8 13.101l-5.223 2.815A.5.5 0 0 1 2 15.5zm2-1a1 1 0 0 0-1 1v12.566l4.723-2.482a.5.5 0 0 1 .554 0L13 14.566V2a1 1 0 0 0-1-1z"/>
        </svg>
    """
)

bookmark_x = ui.HTML(
    """
        <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" fill="currentColor" class="bi bi-bookmark-x" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M6.146 5.146a.5.5 0 0 1 .708 0L8 6.293l1.146-1.147a.5.5 0 1 1 .708.708L8.707 7l1.147 1.146a.5.5 0 0 1-.708.708L8 7.707 6.854 8.854a.5.5 0 1 1-.708-.708L7.293 7 6.146 5.854a.5.5 0 0 1 0-.708"/>
            <path d="M2 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v13.5a.5.5 0 0 1-.777.416L8 13.101l-5.223 2.815A.5.5 0 0 1 2 15.5zm2-1a1 1 0 0 0-1 1v12.566l4.723-2.482a.5.5 0 0 1 .554 0L13 14.566V2a1 1 0 0 0-1-1z"/>
        </svg>
    """
)


logo = ui.HTML(
    f"""
       <img src="https://www.mpie.de/assets/og-logo-281c44f14f2114ed3fe50e666618ff96341055a2f8ce31aa0fd70471a30ca9ed.jpg" width="50" height="50" style="margin-right: 10px;">
    """
)

ui.page_opts(
    title=ui.HTML(f"""
        <div style="display: flex; align-items: center;">
            {logo}
            <span>Open Science Dashboard MPG</span>
        </div>
    """),
    fillable=True,
    window_title=ui.HTML(f"""
        Open Science Dashboard MPG
    """)
)

with ui.sidebar(title="Filter Daten"):
    ui.input_checkbox_group(  
    "checkbox_group",  
    "Genres",  
    {  
        "ARTICLE": "Forschungspapiere",  
        "CONFERENCE_PAPER": "Konferenzbeiträge",  
        "BOOK_ITEM": "Buchbeiträge",  
        "OTHERS": "Andere",  
    }, selected=["ARTICLE", "CONFERENCE_PAPER", "BOOK_ITEM", "OTHERS"]
) 
    ui.input_date_range("daterange", "Zeitraum", start="2022-01-01", end="2023-12-31", min="2022-01-01", max="2023-12-31")  




with ui.layout_column_wrap():
    with ui.value_box(
        showcase=book,
        theme="bg-gradient-white",  
    ):
        @render.ui()
        def value_box():
            start_date = input.daterange()[0]
            end_date = input.daterange()[1]
            start_date = start_date.strftime("%d.%m.%Y")
            end_date = end_date.strftime("%d.%m.%Y")
            return f"# Publikationen ({start_date}-{end_date})"
        @render.ui()
        def value_box1():
            global publications
            start_date = input.daterange()[0]
            end_date = input.daterange()[1]
            genres = input.checkbox_group()
            publications = get_publications(start_date, end_date, genres)
            print("Publications: ",len(publications))
            summe_publikationen = len(publications)
            return f'{summe_publikationen:,}'


    with ui.value_box(
        showcase=bookmark,
        theme="success",  
    ):
        "# OA Publikationen 2022-2023"
        @render.ui()
        def oa_publications():
            global oa_publications_list
            start_date = input.daterange()[0]
            end_date = input.daterange()[1]
            genres = input.checkbox_group()
            oa_publications_list = get_oa_publications(start_date, end_date, 'true', genres)
            print("Publications: ",len(oa_publications_list))
            summe_publikationen = len(oa_publications_list)
            return f'{summe_publikationen:,}'

    with ui.value_box(
        showcase=bookmark_x,
        theme="danger",  
    ):
        "# CA Publikationen 2022-2023"
        @render.ui()
        def ca_publications():
            global ca_publications_list
            start_date = input.daterange()[0]
            end_date = input.daterange()[1]
            genres = input.checkbox_group()
            ca_publications_list = get_oa_publications(start_date, end_date, 'false', genres)
            print("Publications: ",len(ca_publications_list))
            summe_publikationen = len(ca_publications_list)
            return f'{summe_publikationen:,}'


with ui.layout_columns(col_widths=(8, 4)):
    with ui.card():
       "Open Access Entwicklung"
       @render.plot()
       def line():
        genres = input.checkbox_group()
        date = input.daterange()
        month_year_counts_ca = Counter(extract_month_year(ca_publication[1]) for ca_publication in ca_publications_list if extract_month_year(ca_publication[1]))
        month_year_counts_oa = Counter(extract_month_year(oa_publication[1]) for oa_publication in oa_publications_list if extract_month_year(oa_publication[1]))
        month_year_counts = Counter(extract_month_year(publication[1]) for publication in publications if extract_month_year(publication[1]))
        # Convert to sorted list of tuples (optional)
        sorted_counts_ca = sorted(month_year_counts_ca.items())
        sorted_counts_oa = sorted(month_year_counts_oa.items())
        sorted_counts = sorted(month_year_counts.items())


        from matplotlib import pyplot as plt
        x_ca = [item[0] for item in sorted_counts_ca]
        y_ca = [item[1] for item in sorted_counts_ca]
        x_oa = [item[0] for item in sorted_counts_oa]
        y_oa = [item[1] for item in sorted_counts_oa]
        x = [item[0] for item in sorted_counts]
        y = [item[1] for item in sorted_counts]
        plt.plot(x, y, label='Alle Publikationen', marker='o')
        plt.plot(x_ca, y_ca, label='Closed Access Publikationen', marker='o')
        plt.plot(x_oa, y_oa, label='Open Access Publikationen', marker='o')
        plt.legend()
        plt.grid(axis='y')
        plt.xticks(rotation=45)
        

    with ui.card():
        "Aufteilung OA, CA und nicht angegeben"

        @render.plot()
        def pie():
            genres = input.checkbox_group()
            date = input.daterange()
            oa_number = len(oa_publications_list)
            ca_number = len(ca_publications_list)
            not_findable_number = len(publications) - (oa_number + ca_number) 
            print(oa_number, ca_number, not_findable_number)
            from matplotlib import pyplot as plt
            # create data
            size_of_groups=[oa_number, ca_number, not_findable_number]
            plt.pie(size_of_groups,  wedgeprops=dict(width=0.3))
            plt.legend(["Open Access", "Closed Access", "Not Findable"], loc='upper right', bbox_to_anchor=(1.5, 1))

with ui.layout_column_wrap():
    with ui.card():
        @render.plot()
        def bar_data():
            from matplotlib import pyplot as plt
            # create data
            y_pos = [0,1,2,3]
            height = [12,11,3,30]
            plt.bar(y_pos, height)
    with ui.card():
        @render.plot()
        def bar_code():
            from matplotlib import pyplot as plt
            # create data
            y_pos = [0,1,2,3]
            height = [12,11,3,30]
            plt.bar(y_pos, height)
def line():
    from matplotlib import pyplot as plt
    plt.plot([1, 2, 3, 4])
