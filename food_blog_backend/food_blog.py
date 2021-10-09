import sys
from typing import List, Dict, Union

import sqlite3
import argparse


def get_meals() -> Dict[int, str]:
    """
    Data access function to select meals and map into dict name_by_number

    :Return mapping name_by_number to meals
    """

    query = cursor.execute(f'''SELECT * FROM meals''').fetchall()
    return_dict = {}
    for item in query:
        return_dict[item[0]] = item[1]
    return return_dict


def get_like_expr(expr: Union[int, str], table_name: str, col_name: str) -> List[Union[str, int]]:
    """
    Return list of objects obtained using the corresponding predicate like expression

    :param expr - predicate to search by
    :param table_name - full name of table
    :param col_name - name of column to search in

    Return: list of objects with @col_name values contains @expr left-sided or right-sided
    """

    query = cursor.execute(f'''SELECT * FROM {table_name}
                            where {col_name} like ?;''', ('%' + expr + '%',)).fetchall()
    return query


def get_exactly_expr(table_name: str, expr: Union[int, str], col_name: str) -> List[Union[str, int]]:
    """
    Return list of objects obtained using where clause

    :param table_name: full name of table contains @col_name
    :param expr: predicate to search by
    :param col_name: name of column to search in

    :Return list of objects with @col_name values equals @expr
    """

    query = cursor.execute(f'''SELECT * FROM {table_name}
                            where {col_name} = ?''', (expr,))
    return query.fetchall()


def get_recipe_by_meal_and_ingredient(meals_: List[int], ingredients_: List[str]) -> Union[List[str], None]:
    """
    Data access function to get recipe by meal and ingredient
    Multiple queries in loop of ingredients, then get their intersection

    :param meals_: list of numbers (integer values), look @get_meals()
    :param ingredients_: list of ingredients

    :Return None if there is no recipe by meal and ingredients. Expected to search by all ingredients
    """

    list_of_sets_ids = []
    for ingredient in ingredients_:
        query = cursor.execute(f'''SELECT t1.recipe_name, t1.recipe_id FROM recipes t1
                            inner join serve t2
                            on t1.recipe_id = t2.recipe_id
                            inner join meals t3
                            on t2.meal_id = t3.meal_id
                            inner join quantity t4
                            on t4.recipe_id = t1.recipe_id
                            join ingredients t5
                            on t5.ingredient_id = t4.ingredient_id
                            where t5.ingredient_name = ? and t3.meal_name in ({",".join(["?"] * len(meals_))});''',
                               (ingredient, *meals_)).fetchall()
        if query:
            list_of_sets_ids.append(set(item[1] for item in query))
    if list_of_sets_ids and len(list_of_sets_ids) == len(ingredients_):
        recipe_ids = set.intersection(*list_of_sets_ids)
    else:
        return None
    return cursor.execute(f'''SELECT recipe_name FROM recipes
                         where recipe_id in ({",".join(["?"] * len(recipe_ids))});''',
                          (*recipe_ids,)).fetchall()


class TableExecutor:
    """
    Abstract class to create tables and insert default values
    """

    default_data = {"meals": ("breakfast", "brunch", "lunch", "supper"),
                    "ingredients": ("milk", "cacao", "strawberry", "blueberry", "blackberry", "sugar"),
                    "measures": ("ml", "g", "l", "cup", "tbsp", "tsp", "dsp", "")}
    global cursor
    global connect

    def create_table(self, table_name: str) -> None:
        """
        Create table by its name & fill constraints

        :param table_name - name of table to create
        """

        id_ = table_name[:-1] + '_id'  # get table_name without last char (s)
        name_ = table_name[:-1] + '_name'  # get table_name without last char (s)
        not_null = 'NOT NULL'
        unique = 'UNIQUE'
        if table_name == 'measures':
            not_null = ''
        elif table_name == 'recipes':
            unique = ''
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table_name}
                            (
                            {id_} INTEGER PRIMARY KEY,
                            {name_} VARCHAR(30) {not_null} {unique}
                            );''')
        connect.commit()
        if table_name != 'recipes':
            self.insert_default_values(table_name)

    def insert_default_values(self, table_name: str) -> None:
        """
        Insert hard-coded default values into table

        :param table_name: name of table to fill data in
        """

        values_attr = table_name[:-1] + '_name'
        query = cursor.execute(f'''SELECT * FROM {table_name}
                                    WHERE {values_attr} = \'{self.default_data[table_name][0]}\'''').fetchall()
        if not query:
            for item in self.default_data[table_name]:
                cursor.execute(f'''INSERT INTO {table_name}({values_attr})
                                    VALUES (\'{item}\')''')
                connect.commit()


class RecipesTable(TableExecutor):
    """Recipe model"""

    table_name = 'recipes'

    def create_table(self, table_name: str = 'recipes') -> None:
        """
        Create recipe table using abstract parent method

        :param table_name: name of table. Default is "recipes"
        """

        super().create_table(table_name)
        column_name = table_name[:-1] + '_description'
        all_cols = cursor.execute(f'''PRAGMA table_info({table_name});''').fetchall()
        checker = [1 for x in all_cols if column_name in x]
        if not checker:
            cursor.execute(f'''ALTER TABLE {table_name}
                                ADD COLUMN {column_name} VARCHAR(80)''')
        connect.commit()

    def insert_and_commit(self, recipe_name: str, recipe_description: str) -> int:
        """
        DAO to insert into database values

        :param recipe_name: name of recipe inserted by user
        :param recipe_description: description of recipe - way of cook the meal
        """

        description = self.table_name[:-1] + '_description'
        name = self.table_name[:-1] + '_name'
        id_ = cursor.execute(f'''INSERT INTO {self.table_name} ({name}, {description})
                            VALUES (?, ?)''', (recipe_name, recipe_description)).lastrowid
        connect.commit()
        return id_

    def process_input(self, serves_table, quantity_table) -> None:
        """
        Process input from user to fill the recipes

        :param serves_table: object of @ServeTable
        :param quantity_table: object of @QuantityTable
        """

        recipe_name = input('Recipe name: ')
        while recipe_name:
            recipe_description = input('Recipe description: ')
            last_row_id = self.insert_and_commit(recipe_name, recipe_description)
            meals_ = get_meals()
            print(*[f'{item}) ' + meals_[item] for item in meals_.keys()])
            chosen_numbers = list(map(int, input('When the dish can be served: ').split()))
            for number in chosen_numbers:
                serves_table.insert_and_commit(last_row_id, number)
            quantity_table.process_input(last_row_id)
            recipe_name = input('Recipe name: ')


class ServeTable(TableExecutor):
    """Broker model to create many-to-many relations of recipes & meals"""

    table_name = 'serve'
    col_1 = 'serve_id'
    col_2 = 'recipe_id'
    col_3 = 'meal_id'

    def create_table(self, table_name: str = 'serve') -> None:
        """
        Create table by SQL query and commit into database

        :param table_name: name of table in database
        """
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table_name} (
                        {self.col_1} INTEGER PRIMARY KEY,
                        {self.col_2} INTEGER NOT NULL,
                        {self.col_3} INTEGER NOT NULL,
                        CONSTRAINT fk_recipes FOREIGN KEY ({self.col_2})
                        REFERENCES recipes ({self.col_2}),
                        CONSTRAINT fk_meals FOREIGN KEY ({self.col_3})
                        REFERENCES meals ({self.col_3})
                        );''')
        connect.commit()

    def insert_and_commit(self, recipe_id: int, meal_id: int) -> None:
        """
        Insert objects in table

        :param recipe_id: id of recipe in recipes table
        :param meal_id: id of meal in meals table
        """
        cursor.execute(f'''INSERT INTO {self.table_name}({self.col_2}, {self.col_3})
                        VALUES (?, ?)''', (recipe_id, meal_id))
        connect.commit()


class QuantityTable(TableExecutor):
    """
    Model of quantity model. Contains relations of recipe & ingredients & quantity & measures
    """

    table_name = 'quantity'
    col_1 = 'quantity_id'
    col_2 = 'measure_id'
    col_3 = 'ingredient_id'
    col_4 = 'quantity'
    col_5 = 'recipe_id'

    def create_table(self, table_name: str = 'quantity') -> None:
        """
        Create table in database. Commit changes

        :param table_name: name of table. Default is "quantity"
        """
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table_name}(
                       {self.col_1} INTEGER PRIMARY KEY,
                       {self.col_2} INTEGER NOT NULL,
                       {self.col_3} INTEGER NOT NULL,
                       {self.col_4} INTEGER NOT NULL,
                       {self.col_5} INTEGER NOT NULL,
                        CONSTRAINT fk_measures FOREIGN KEY ({self.col_2})
                        REFERENCES measures ({self.col_2}),
                        CONSTRAINT fk_ingredients FOREIGN KEY ({self.col_3})
                        REFERENCES ingredients ({self.col_3}),
                        CONSTRAINT fk_recipes FOREIGN KEY ({self.col_5})
                        REFERENCES recipes ({self.col_5}))''')

    def insert_and_commit(self, measure_id: int, ingredient_id: int, quantity_: int, recipe_id: int) -> None:
        """
        Insert values by ids of related objects

        :param measure_id: id of object in @measures
        :param ingredient_id: id of object in @ingredients
        :param quantity_: count of corresponding ingredient
        :param recipe_id: id of object in @RecipesTable
        """
        cursor.execute(f'''INSERT INTO {self.table_name} ({self.col_2}, {self.col_3}, {self.col_4}, {self.col_5})
                        VALUES (?, ?, ?, ?);''', (measure_id, ingredient_id, quantity_, recipe_id))
        connect.commit()

    def process_input(self, recipe_id: int) -> None:
        """
        Process inserts of user's choices

        :param recipe_id: id of object in @RecipesTable
        """
        list_of_input = True
        while list_of_input:
            list_of_input = input('Input quantity of ingredient <press enter to stop>: ').split()
            if not list_of_input:
                break
            quantity_ = int(list_of_input[0])
            if len(list_of_input) == 2:
                measure = ''
                ingredient = list_of_input[1]
                like_ingredients = get_like_expr(ingredient, 'ingredients', 'ingredient_name')
                if len(like_ingredients) > 1:
                    print('The ingredient is not conclusive!')
                    continue
                else:
                    measure_id = get_exactly_expr('measures', measure, 'measure_name')
                    self.insert_and_commit(int(measure_id[0][0]), int(like_ingredients[0][0]),
                                           quantity_, recipe_id)
            elif len(list_of_input) == 3:
                measure = list_of_input[1]
                like_measure = get_like_expr(measure, 'measures', 'measure_name')
                if len(like_measure) > 1:
                    print('The measure is not conclusive!')
                    continue
                ingredient = list_of_input[2]
                like_ingredients = get_like_expr(ingredient, 'ingredients', 'ingredient_name')
                if len(like_ingredients) == 2:
                    print('The ingredient is not conclusive!')
                    continue
                self.insert_and_commit(int(like_measure[0][0]), int(like_ingredients[0][0]),
                                       quantity_, recipe_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Provide interface to recipes book')
    parser.add_argument('data_base', help='Relative path to db file', type=str)
    parser.add_argument('--ingredients', '-i', required=False, help='List of ingredients')
    parser.add_argument('--meals', '-m', required=False, help='List of meals')
    if len(sys.argv) < 1:
        print('Error argument db name')
    args = parser.parse_args()
    database_name = args.data_base
    ingredients = args.ingredients.split(',') if args.ingredients else None
    meals = args.meals.split(',') if args.meals else None
    connect = sqlite3.connect(database_name)
    cursor = connect.cursor()
    cursor.execute('''PRAGMA foreign_keys = ON;''')
    connect.commit()
    executor = TableExecutor()
    list_of_tables = ['meals', 'ingredients', 'measures']
    for table in list_of_tables:
        executor.create_table(table)
    recipes = RecipesTable()
    recipes.create_table()
    serves = ServeTable()
    serves.create_table()
    quantity = QuantityTable()
    quantity.create_table()
    if not (ingredients and meals):
        recipes.process_input(serves, quantity)
    else:
        res = get_recipe_by_meal_and_ingredient(meals, ingredients)
        if res:
            print(f'Recipes selected for you: {", ".join(res[i][0] for i in range(len(res)))}')
        else:
            print('There are no such recipes in the database.')
    connect.close()
