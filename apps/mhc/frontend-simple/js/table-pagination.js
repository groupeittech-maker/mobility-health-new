(() => {
    const paginations = new Map();

    function getPagerElements(wrapper) {
        return {
            wrapper,
            info: wrapper.querySelector('.table-pager-info'),
            prev: wrapper.querySelector('.table-pager-prev'),
            next: wrapper.querySelector('.table-pager-next'),
        };
    }

    function createPager(tbody, state) {
        const pager = document.createElement('div');
        pager.className = 'table-pager';
        pager.innerHTML = `
            <button type="button" class="table-pager-btn table-pager-prev" aria-label="Page précédente">◀</button>
            <span class="table-pager-info">Page 1</span>
            <button type="button" class="table-pager-btn table-pager-next" aria-label="Page suivante">▶</button>
        `;
        tbody.parentElement?.appendChild(pager);
        const els = getPagerElements(pager);
        els.prev.addEventListener('click', () => changePage(state, -1));
        els.next.addEventListener('click', () => changePage(state, 1));
        state.pagerElements = els;
    }

    function changePage(state, offset) {
        const totalPages = Math.ceil(state.rows.length / state.pageSize);
        state.page = Math.max(0, Math.min(totalPages - 1, state.page + offset));
        renderPage(state);
    }

    function renderPage(state) {
        const tbody = state.tbody;
        if (!tbody) {
            return;
        }
        const start = state.page * state.pageSize;
        const end = start + state.pageSize;
        tbody.innerHTML = state.rows.slice(start, end).join('');
        const totalPages = Math.max(1, Math.ceil(state.rows.length / state.pageSize));
        if (state.pagerElements) {
            state.pagerElements.info.textContent = `Page ${state.page + 1} / ${totalPages}`;
            state.pagerElements.prev.disabled = state.page === 0;
            state.pagerElements.next.disabled = state.page >= totalPages - 1;
        }
    }

    function removePager(tbodyId) {
        const state = paginations.get(tbodyId);
        if (state && state.pagerElements?.wrapper) {
            state.pagerElements.wrapper.remove();
        }
        paginations.delete(tbodyId);
    }

    function paginateTable(tbodyId, options = {}) {
        const pageSize = Number(options.pageSize) || 6;
        const tbody = document.getElementById(tbodyId);
        if (!tbody) {
            return;
        }
        const rows = Array.from(tbody.querySelectorAll('tr')).map((row) => row.outerHTML);
        if (rows.length <= pageSize) {
            removePager(tbodyId);
            return;
        }
        let state = paginations.get(tbodyId);
        if (!state) {
            state = { page: 0, pageSize, tbody };
            createPager(tbody, state);
        }
        state.rows = rows;
        state.page = Math.min(state.page, Math.ceil(rows.length / pageSize) - 1);
        renderPage(state);
        paginations.set(tbodyId, state);
    }

    function createListPager(listEl, state) {
        const pager = document.createElement('div');
        pager.className = 'table-pager';
        pager.innerHTML = `
            <button type="button" class="table-pager-btn table-pager-prev" aria-label="Page précédente">◀</button>
            <span class="table-pager-info">Page 1</span>
            <button type="button" class="table-pager-btn table-pager-next" aria-label="Page suivante">▶</button>
        `;
        listEl.after(pager);
        const els = getPagerElements(pager);
        els.prev.addEventListener('click', () => changeListPage(state, -1));
        els.next.addEventListener('click', () => changeListPage(state, 1));
        state.pagerElements = els;
    }

    function changeListPage(state, offset) {
        const totalPages = Math.ceil(state.items.length / state.pageSize);
        state.page = Math.max(0, Math.min(totalPages - 1, state.page + offset));
        renderListPage(state);
    }

    function renderListPage(state) {
        const list = state.list;
        if (!list) {
            return;
        }
        const start = state.page * state.pageSize;
        const end = start + state.pageSize;
        list.innerHTML = state.items.slice(start, end).join('');
        const totalPages = Math.max(1, Math.ceil(state.items.length / state.pageSize));
        if (state.pagerElements) {
            state.pagerElements.info.textContent = `Page ${state.page + 1} / ${totalPages}`;
            state.pagerElements.prev.disabled = state.page === 0;
            state.pagerElements.next.disabled = state.page >= totalPages - 1;
        }
    }

    function removeListPager(listId) {
        const key = `list:${listId}`;
        const state = paginations.get(key);
        if (state && state.pagerElements?.wrapper) {
            state.pagerElements.wrapper.remove();
        }
        paginations.delete(key);
    }

    function paginateList(listId, options = {}) {
        const pageSize = Number(options.pageSize) || 6;
        const list = document.getElementById(listId);
        if (!list) {
            return;
        }
        const key = `list:${listId}`;
        const items = Array.from(list.querySelectorAll(':scope > li')).map((li) => li.outerHTML);
        if (items.length <= pageSize) {
            removeListPager(listId);
            return;
        }
        let state = paginations.get(key);
        if (!state) {
            state = { page: 0, pageSize, list };
            createListPager(list, state);
        }
        state.items = items;
        state.page = Math.min(state.page, Math.ceil(items.length / pageSize) - 1);
        renderListPage(state);
        paginations.set(key, state);
    }

    window.paginateTable = paginateTable;
    window.paginateList = paginateList;
})();

