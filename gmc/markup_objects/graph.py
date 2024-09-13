from PyQt5 import QtCore, QtGui, QtWidgets
from gmc.markup_objects import MarkupObjectMeta
from collections import namedtuple

Qt = QtCore.Qt


class MarkupNode(QtWidgets.QGraphicsItem, MarkupObjectMeta):
    _bounding_rect = QtCore.QRectF(-8.0, -8.0, 16.0, 16.0)
    _rect = QtCore.QRectF(-4.0, -4.0, 8.0, 8.0)
    _shape = QtGui.QPainterPath()
    _shape.addEllipse(_bounding_rect)
    BRUSH = QtGui.QBrush(QtGui.QColor(0, 0, 0, 127))
    PEN = QtGui.QPen(QtGui.QColor("orange"))

    def __init__(self, node_id, pos, meta=None):
        if node_id is None:
            import uuid

            node_id = str(uuid.uuid1())
        assert isinstance(node_id, (str, int)), node_id
        self.node_id = node_id
        self.meta = meta
        self._edges = set()
        super(MarkupNode, self).__init__()
        self.setZValue(1000)
        self.setPos(pos)
        self.setFlags(
            self.ItemIgnoresTransformations
            | self.ItemIsMovable
            | self.ItemIsSelectable
            | self.ItemIsFocusable
            | self.ItemSendsGeometryChanges
        )

    def itemChange(self, change, value):
        if change == self.ItemPositionHasChanged:
            for edge in self._edges:
                edge.notify(self, value)
        return value

    def paint(self, painter, option, widget):
        painter.setPen(self.PEN)
        painter.drawEllipse(self._rect)
        if self.isSelected():
            painter.setBrush(self.BRUSH)
            painter.setPen(QtGui.QPen(Qt.NoPen))
            painter.drawEllipse(self._rect)

    def boundingRect(self):
        return self._bounding_rect

    def shape(self):
        return self._shape

    def on_start_edit(self):
        pass

    def on_stop_edit(self):
        pass

    def on_edges_changed(self):
        pass

    def attach(self, view):
        view.set_mouse_press(self.mouse_press)

    def mouse_press(self, event, view):
        self.setPos(view.mapToScene(event.pos()))
        view.set_mouse_move(self.mouse_move)
        view.set_mouse_release(self.mouse_release)
        view.set_cancel(self.cancel)
        view.scene().addItem(self)

    def mouse_move(self, event, view):
        self.setPos(view.mapToScene(event.pos()))
        self.update()

    def mouse_release(self, event, view):
        self.mouse_move(event, view)
        view.unset_all_events()
        self.setFlag(self.ItemIsSelectable, True)

    def cancel(self, view):
        view.unset_all_events()
        self.delete()

    def delete(self):
        scene = self.scene()
        for edge in list(self._edges):
            edge.delete()
            scene.removeItem(edge)
        return True

    def direct_connection_edges(self, other):
        assert isinstance(other, MarkupNode)
        return self._edges & other._edges

    def in_out(self):
        in_list, out_list = [], []
        for edge in self._edges:
            if edge.u is self:
                out_list.append(edge)
            elif edge.v is self:
                in_list.append(edge)
            else:
                raise AssertionError("invalid edge", edge)
        return in_list, out_list


class MarkupEdge(QtWidgets.QGraphicsItem):
    PEN = MarkupObjectMeta.PEN
    PEN_DASHED = MarkupObjectMeta.PEN_DASHED
    PEN_SELECTED = MarkupObjectMeta.PEN_SELECTED
    PEN_SELECTED_DASHED = MarkupObjectMeta.PEN_SELECTED_DASHED

    def __init__(self, u, v, meta=None):
        super(MarkupEdge, self).__init__()
        assert u is not v  # for no real reason
        self.u = u
        self.v = v
        u._edges.add(self)
        u.on_edges_changed()
        v._edges.add(self)
        v.on_edges_changed()
        self.meta = meta
        self._line = QtCore.QLineF(u.pos(), v.pos())
        self._rc = QtCore.QRectF(self._line.p1(), self._line.p2()).normalized()
        self.setZValue(999)
        self.setFlags(self.ItemIsSelectable | self.ItemIsFocusable)

    def boundingRect(self):
        return self._rc

    def shape(self):
        path = QtGui.QPainterPath()
        path.moveTo(self._line.p1())
        path.lineTo(self._line.p2())
        ps = QtGui.QPainterPathStroker()
        ps.setWidth(9.0)
        return ps.createStroke(path)

    def paint(self, painter, option, widget):
        if self.isSelected():
            pen1, pen2 = self.PEN, self.PEN_DASHED
        else:
            pen1, pen2 = self.PEN_SELECTED, self.PEN_SELECTED_DASHED
        painter.setPen(pen1)
        painter.drawLine(self._line)
        painter.setPen(pen2)
        painter.drawLine(self._line)

    def notify(self, node, pos):
        if node is self.u:
            self._line.setP1(pos)
        elif node is self.v:
            self._line.setP2(pos)
        else:
            raise AssertionError("invalid node in `notify`", node)
        self.prepareGeometryChange()
        self._rc = QtCore.QRectF(self._line.p1(), self._line.p2()).normalized()
        self.update()

    def delete(self):
        for node in self.u, self.v:
            try:
                node._edges.remove(self)
            except KeyError:  # when multiple objects are deleted at once
                continue
            node.on_edges_changed()
        return True

    def change_direction(self):
        self.u, self.v = self.v, self.u
        self._line = QtCore.QLineF(self.u.pos(), self.v.pos())
        self.u.on_edges_changed()  # call `on_edges_changed`, since
        self.v.on_edges_changed()  # this edge data has changed
        self.update()

    def connect_u(self, new_u):
        assert new_u is not self.v
        self.u._edges.remove(self)
        self.u.on_edges_changed()
        self.u = new_u
        new_u._edges.add(self)
        self.notify(new_u, new_u.pos())
        new_u.on_edges_changed()

    def connect_v(self, new_v):
        assert new_v is not self.u
        self.v._edges.remove(self)
        self.v.on_edges_changed()
        self.v = new_v
        new_v._edges.add(self)
        self.notify(new_v, new_v.pos())
        new_v.on_edges_changed()


Node = namedtuple("Node", ("id", "pos", "meta"))
Edge = namedtuple("Edge", ("u", "v", "meta"))


def create_graph(nodes, edges, node_cls=MarkupNode, edge_cls=MarkupEdge):
    """
    :param nodes: list of `Node`
    :param edges: list of `Edge`
    """
    nodes_dict = {}
    for node in nodes:
        m_node = node_cls(node.id, node.pos, node.meta)
        yield m_node
        if node.id in nodes_dict:
            raise AssertionError("Duplicate node id", node.id)
        nodes_dict[node.id] = m_node
    for edge in edges:
        m_edge = edge_cls(nodes_dict[edge.u], nodes_dict[edge.v], edge.meta)
        yield m_edge
