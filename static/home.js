(function () {
    const desktop = document.getElementById('home-desktop');
    if (!desktop) return;

    const arrangeUrl = desktop.dataset.arrangeUrl;
    const homeUrl = desktop.dataset.homeUrl || '/';
    const HOLD_MS = 360;
    const MOVE_PX = 12;
    let press = null;
    let drag = null;
    let suppressClick = false;

    function csrfToken() {
        const field = document.querySelector('[name=csrfmiddlewaretoken]');
        if (field && field.value) return field.value;
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function post(payload) {
        return fetch(arrangeUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
            },
            body: JSON.stringify(payload),
        }).then(function (response) {
            if (!response.ok) throw new Error('arrange failed');
            return response.json();
        });
    }

    function homePayload() {
        return [...desktop.querySelectorAll(':scope > .home-item')].map(function (el) {
            return { type: el.dataset.type, id: Number(el.dataset.id) };
        }).filter(function (item) { return item.type && item.id; });
    }

    function pickupTarget(event) {
        const item = event.target.closest('.home-item');
        if (!item || !desktop.contains(item) || item.dataset.open === '1') return null;
        if (item.dataset.type === 'bookmark' || item.dataset.type === 'folder') return item;
        return null;
    }

    function clearDrop() {
        desktop.querySelectorAll('.is-drop-on').forEach(function (el) {
            el.classList.remove('is-drop-on');
        });
    }

    function hit(x, y, ghost) {
        ghost.style.visibility = 'hidden';
        const el = document.elementFromPoint(x, y);
        ghost.style.visibility = 'visible';
        if (!el) return {};
        const app = el.closest('.home-item[data-type="bookmark"]');
        const folderItem = el.closest('.home-item[data-type="folder"]');
        const closedFolder = folderItem && folderItem.dataset.open !== '1' ? folderItem : null;
        const tray = el.closest('.folder-tray');
        return { el, app, closedFolder, tray, desktop: el.closest('#home-desktop') };
    }

    function insertIndex(items, x, y) {
        for (let i = 0; i < items.length; i += 1) {
            const box = items[i].getBoundingClientRect();
            if (y < box.top) return i;
            const sameRow = y <= box.bottom && y >= box.top;
            if (sameRow && x < box.left + box.width / 2) return i;
        }
        return items.length;
    }

    function placeAmong(container, dragged, x, y) {
        const others = [...container.children].filter(function (child) {
            return child.classList.contains('home-item') && child !== dragged;
        });
        const index = insertIndex(others, x, y);
        const target = others[index];
        if (target) container.insertBefore(dragged, target);
        else container.appendChild(dragged);
    }

    function startDrag(event, item) {
        if (drag) return;
        const box = item.getBoundingClientRect();
        const ghost = item.cloneNode(true);
        ghost.id = 'drag-ghost';
        ghost.style.width = box.width + 'px';
        ghost.style.left = (event.clientX - (event.clientX - box.left)) + 'px';
        ghost.style.top = (event.clientY - (event.clientY - box.top)) + 'px';
        document.body.appendChild(ghost);
        item.classList.add('is-ghost');
        document.body.classList.add('is-dragging');
        item.setPointerCapture(event.pointerId);
        if (navigator.vibrate) navigator.vibrate(8);
        drag = {
            el: item,
            ghost,
            offsetX: event.clientX - box.left,
            offsetY: event.clientY - box.top,
            moved: false,
        };
        suppressClick = true;
        moveGhost(event.clientX, event.clientY);
    }

    function moveGhost(x, y) {
        if (!drag) return;
        drag.ghost.style.left = (x - drag.offsetX) + 'px';
        drag.ghost.style.top = (y - drag.offsetY) + 'px';
        clearDrop();
        const over = hit(x, y, drag.ghost);
        const type = drag.el.dataset.type;
        if (type === 'bookmark' && over.closedFolder) {
            over.closedFolder.classList.add('is-drop-on');
            return;
        }
        if (type === 'bookmark' && over.app && over.app !== drag.el && !over.app.dataset.folder && !drag.el.dataset.folder) {
            over.app.classList.add('is-drop-on');
            return;
        }
        drag.moved = true;
        if (drag.el.dataset.folder) {
            const tray = drag.el.closest('.folder-apps');
            if (tray && over.tray && over.tray.contains(tray)) {
                placeAmong(tray, drag.el, x, y);
            }
            return;
        }
        if (drag.el.parentElement === desktop) {
            placeAmong(desktop, drag.el, x, y);
        }
    }

    function finish(x, y) {
        if (!drag) return;
        const item = drag.el;
        const type = item.dataset.type;
        const id = Number(item.dataset.id);
        const fromFolder = item.dataset.folder ? Number(item.dataset.folder) : null;
        const over = hit(x, y, drag.ghost);
        const ghost = drag.ghost;
        item.classList.remove('is-ghost');
        document.body.classList.remove('is-dragging');
        ghost.remove();
        drag = null;
        clearDrop();

        const reload = function () { window.location.reload(); };
        const fail = function () { window.location.reload(); };

        if (type === 'bookmark') {
            if (over.closedFolder) {
                post({
                    op: 'move',
                    bookmark_id: id,
                    folder_id: Number(over.closedFolder.dataset.id),
                    index: 999,
                }).then(reload).catch(fail);
                return;
            }
            if (over.app && Number(over.app.dataset.id) !== id && !over.app.dataset.folder && !fromFolder) {
                post({
                    op: 'stack',
                    bookmark_id: id,
                    onto_bookmark_id: Number(over.app.dataset.id),
                }).then(function (data) {
                    window.location.href = data.folder_id ? homeUrl + '?open=' + data.folder_id : homeUrl;
                }).catch(fail);
                return;
            }
            if (fromFolder && over.tray && Number(over.tray.dataset.id) === fromFolder) {
                const ids = [...over.tray.querySelectorAll('.home-item[data-type="bookmark"]')].map(function (el) {
                    return Number(el.dataset.id);
                });
                post({ op: 'reorder_folder', folder_id: fromFolder, bookmark_ids: ids }).catch(fail);
                return;
            }
            if (fromFolder) {
                const idx = insertIndex(
                    [...desktop.querySelectorAll(':scope > .home-item')].filter(function (el) { return el !== item; }),
                    x,
                    y,
                );
                post({ op: 'move', bookmark_id: id, folder_id: null, index: idx }).then(reload).catch(fail);
                return;
            }
            post({ op: 'reorder_home', items: homePayload() }).catch(fail);
            return;
        }
        if (type === 'folder') {
            post({ op: 'reorder_home', items: homePayload() }).catch(fail);
        }
    }

    function cancelPress() {
        if (press && press.timer) window.clearTimeout(press.timer);
        press = null;
    }

    desktop.addEventListener('pointerdown', function (event) {
        if (event.button !== 0) return;
        const item = pickupTarget(event);
        if (!item) return;
        const startX = event.clientX;
        const startY = event.clientY;
        const isTouch = event.pointerType === 'touch';
        press = { item, startX, startY, pointerId: event.pointerId };
        press.timer = window.setTimeout(function () {
            if (!press || press.item !== item) return;
            startDrag(event, item);
        }, isTouch ? HOLD_MS : 180);
    });

    desktop.addEventListener('pointermove', function (event) {
        if (drag && drag.el.hasPointerCapture(event.pointerId)) {
            event.preventDefault();
            moveGhost(event.clientX, event.clientY);
            return;
        }
        if (!press) return;
        const dx = event.clientX - press.startX;
        const dy = event.clientY - press.startY;
        const dist = Math.hypot(dx, dy);
        if (event.pointerType === 'touch' && dist > MOVE_PX && !drag) {
            cancelPress();
            return;
        }
        if (dist > MOVE_PX && press) {
            const item = press.item;
            cancelPress();
            startDrag(event, item);
            moveGhost(event.clientX, event.clientY);
        }
    }, { passive: false });

    function endPointer(event) {
        if (drag) {
            event.preventDefault();
            finish(event.clientX, event.clientY);
            window.setTimeout(function () { suppressClick = false; }, 250);
            return;
        }
        cancelPress();
    }

    desktop.addEventListener('pointerup', endPointer);
    desktop.addEventListener('pointercancel', endPointer);

    desktop.addEventListener('click', function (event) {
        if (!suppressClick) return;
        event.preventDefault();
        event.stopPropagation();
    }, true);
})();
