describe('template spec', () => {
  it('passes', () => {
    cy.visit('https://example.cypress.io')
  })
})


describe('TodoMVC E2E Tests', () => {
  beforeEach(() => {
      cy.visit('http://localhost:8080'); // Открываем приложение
  });

  it('Добавление новой задачи', () => {
      cy.get('.new-todo')
        .type('Купить молоко{enter}'); // Вводим задачу и нажимаем Enter
      
      cy.get('.todo-list li')
        .should('contain.text', 'Купить молоко'); // Проверяем, что задача добавлена
  });

  it('Отметка задачи как выполненной', () => {
    cy.get('.new-todo')
      .type('Купить хлеб{enter}'); // Добавляем задачу

    cy.get('.todo-list li')
      .contains('Купить хлеб')
      .parent()
      .find('.toggle')
      .click(); // Отмечаем как выполненную

    cy.get('.todo-list li.completed')
      .should('have.class', 'completed')
      .should('contain.text', 'Купить хлеб'); // Проверяем, что задача зачёркнута
});

it('Фильтрация задач (Active / Completed)', () => {
  cy.get('.new-todo').type('Сделать зарядку{enter}');
  cy.get('.new-todo').type('Приготовить обед{enter}');
  
  cy.get('.todo-list li')
    .contains('Сделать зарядку')
    .parent()
    .find('.toggle')
    .click(); // Отмечаем как выполненную
  
  cy.get('.filters').contains('Active').click(); // Фильтр "Активные"
  cy.get('.todo-list li')
    .should('contain.text', 'Приготовить обед')
    .and('not.contain.text', 'Сделать зарядку');
  
  cy.get('.filters').contains('Completed').click(); // Фильтр "Выполненные"
  cy.get('.todo-list li')
    .should('contain.text', 'Сделать зарядку')
    .and('not.contain.text', 'Приготовить обед');
  
  cy.get('.filters').contains('All').click(); // Фильтр "Все"
  cy.get('.todo-list li')
    .should('contain.text', 'Сделать зарядку')
    .and('contain.text', 'Приготовить обед');
});
it('Редактирование задачи', () => {
  cy.get('.new-todo').type('Почитать книгу{enter}');

  cy.get('.todo-list li label')
    .contains('Почитать книгу')
    .dblclick({ force: true });

  // Теперь ищем `input` внутри `.input-container`
  cy.get('.todo-list li .input-container input')
    .should('be.visible')
    .clear()
    .type('Посмотреть фильм{enter}');

  cy.get('.todo-list li label').should('contain.text', 'Посмотреть фильм');
});
it('Удаление задачи через крестик', () => {
  cy.get('.new-todo').type('Купить молоко{enter}');

  cy.get('.todo-list li')
    .contains('Купить молоко')
    .parent() // Переходим к родителю элемента (li)
    .find('.destroy') // Ищем кнопку удаления
    .click({ force: true }); // Принудительно кликаем, если элемент скрыт

  cy.get('.todo-list li').should('not.exist'); // Проверяем, что задачи нет
});
it('Удаление выполненных задач через "Clear completed"', () => {
  cy.get('.new-todo')
    .type('Выкинуть мусор{enter}'); // Добавляем задачу

  cy.get('.todo-list li')
    .contains('Выкинуть мусор')
    .parent()
    .find('.toggle')
    .click(); // Отмечаем задачу как выполненную

  cy.contains('Clear completed').click(); // Нажимаем "Clear completed"

  cy.get('.todo-list li')
    .should('not.exist'); // Проверяем, что задачи нет
});
it('Отмечает все задачи как выполненные и снимает отметку', () => {
  cy.get('.new-todo').type('Задача 1{enter}');
  cy.get('.new-todo').type('Задача 2{enter}');
  cy.get('.new-todo').type('Задача 3{enter}');

  // Нажимаем Toggle All
  cy.get('#toggle-all').click();

  // Проверяем, что все задачи выполнены
  cy.get('.todo-list li').should('have.class', 'completed');

  // Нажимаем Toggle All снова
  cy.get('#toggle-all').click();

  // Проверяем, что все задачи снова активны
  cy.get('.todo-list li').should('not.have.class', 'completed');
});
});
