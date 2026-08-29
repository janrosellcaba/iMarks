(function () {
    const desktop = document.getElementById('home-desktop');
    if (!desktop) return;

    const arrangeUrl = desktop.dataset.arrangeUrl;
    const homeUrl = desktop.dataset.homeUrl || '/';
    const HOLD_MS = 360;
    const MOVE_PX = 6;
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
        if (!item || item.dataset.open === '1') return null;
        const inDesktop = desktop.contains(item);
        const inTray = item.closest('.folder-tray');
        if (!inDesktop && !inTray) return null;
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

    function openItem(item) {
        const link = item.querySelector('a[href]');
        if (!link) return;
        if (link.target === '_blank') {
            window.open(link.href, '_blank', 'noopener,noreferrer');
        } else {
            window.location.href = link.href;
        }
    }

    function startDrag(event, item) {
        if (drag) return;
        const box = item.getBoundingClientRect();
        const ghost = item.cloneNode(true);
        ghost.id = 'drag-ghost';
        ghost.style.width = box.width + 'px';
        ghost.style.left = box.left + 'px';
        ghost.style.top = box.top + 'px';
        document.body.appendChild(ghost);
        item.classList.add('is-ghost');
        document.body.classList.add('is-dragging');
        try { item.setPointerCapture(event.pointerId); } catch (error) {}
        drag = {
            el: item,
            ghost,
            offsetX: event.clientX - box.left,
            offsetY: event.clientY - box.top,
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

    function unbindDocument() {
        document.removeEventListener('pointermove', onPointerMove);
        document.removeEventListener('pointerup', onPointerUp);
        document.removeEventListener('pointercancel', onPointerUp);
    }

    function cancelPress() {
        if (press && press.timer) window.clearTimeout(press.timer);
        press = null;
        unbindDocument();
    }

    function onPointerMove(event) {
        if (press && event.pointerId !== press.pointerId) return;
        if (drag) {
            event.preventDefault();
            moveGhost(event.clientX, event.clientY);
            return;
        }
        if (!press) return;
        const dist = Math.hypot(event.clientX - press.startX, event.clientY - press.startY);
        if (press.pointerType === 'touch' && dist > MOVE_PX && !press.lifted) {
            cancelPress();
            return;
        }
        if (dist > MOVE_PX) {
            const item = press.item;
            const pointerId = press.pointerId;
            if (press.timer) window.clearTimeout(press.timer);
            press.timer = null;
            press.lifted = true;
            startDrag(event, item);
            try { item.setPointerCapture(pointerId); } catch (error) {}
            moveGhost(event.clientX, event.clientY);
        }
    }

    function onPointerUp(event) {
        if (press && event.pointerId !== press.pointerId) return;
        if (drag) {
            event.preventDefault();
            finish(event.clientX, event.clientY);
            cancelPress();
            window.setTimeout(function () { suppressClick = false; }, 250);
            return;
        }
        const item = press && press.item;
        const wasMouse = press && press.pointerType !== 'touch';
        cancelPress();
        if (item && wasMouse) {
            suppressClick = true;
            openItem(item);
            window.setTimeout(function () { suppressClick = false; }, 250);
        }
    }

    document.addEventListener('pointerdown', function (event) {
        if (event.button !== 0) return;
        const item = pickupTarget(event);
        if (!item) return;
        if (event.pointerType !== 'touch') {
            event.preventDefault();
        }
        press = {
            item: item,
            startX: event.clientX,
            startY: event.clientY,
            pointerId: event.pointerId,
            pointerType: event.pointerType,
            lifted: false,
        };
        document.addEventListener('pointermove', onPointerMove, { passive: false });
        document.addEventListener('pointerup', onPointerUp);
        document.addEventListener('pointercancel', onPointerUp);
        if (event.pointerType === 'touch') {
            press.timer = window.setTimeout(function () {
                if (!press || press.item !== item) return;
                press.lifted = true;
                startDrag(event, item);
            }, HOLD_MS);
        }
    });

    document.addEventListener('click', function (event) {
        if (!suppressClick) return;
        event.preventDefault();
        event.stopPropagation();
    }, true);

    document.addEventListener('dragstart', function (event) {
        if (event.target.closest && event.target.closest('.home-item')) {
            event.preventDefault();
        }
    });
})();
