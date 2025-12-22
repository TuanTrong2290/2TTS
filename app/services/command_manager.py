"""Command pattern implementation for undo/redo functionality"""
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Callable
from dataclasses import dataclass
from copy import deepcopy


class Command(ABC):
    """Base command interface"""
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @abstractmethod
    def execute(self) -> bool:
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        pass


@dataclass
class CommandResult:
    """Result of command execution"""
    success: bool
    message: str = ""
    data: Any = None


class AddLinesCommand(Command):
    """Command to add lines to project"""
    
    def __init__(self, project, lines: List, insert_index: Optional[int] = None):
        self._project = project
        self._lines = deepcopy(lines)
        self._insert_index = insert_index
        self._added_indices: List[int] = []
    
    @property
    def description(self) -> str:
        return f"Add {len(self._lines)} line(s)"
    
    def execute(self) -> bool:
        try:
            if self._insert_index is not None:
                for i, line in enumerate(self._lines):
                    self._project.lines.insert(self._insert_index + i, line)
                    self._added_indices.append(self._insert_index + i)
            else:
                start_idx = len(self._project.lines)
                for i, line in enumerate(self._lines):
                    line.index = start_idx + i
                    self._project.lines.append(line)
                    self._added_indices.append(start_idx + i)
            
            self._reindex()
            return True
        except:
            return False
    
    def undo(self) -> bool:
        try:
            for idx in sorted(self._added_indices, reverse=True):
                if idx < len(self._project.lines):
                    del self._project.lines[idx]
            self._reindex()
            return True
        except:
            return False
    
    def _reindex(self):
        for i, line in enumerate(self._project.lines):
            line.index = i


class DeleteLinesCommand(Command):
    """Command to delete lines from project"""
    
    def __init__(self, project, indices: List[int]):
        self._project = project
        self._indices = sorted(indices)
        self._deleted_lines: List[tuple] = []  # (index, line)
    
    @property
    def description(self) -> str:
        return f"Delete {len(self._indices)} line(s)"
    
    def execute(self) -> bool:
        try:
            self._deleted_lines.clear()
            for idx in sorted(self._indices, reverse=True):
                if idx < len(self._project.lines):
                    line = deepcopy(self._project.lines[idx])
                    self._deleted_lines.append((idx, line))
                    del self._project.lines[idx]
            
            self._deleted_lines.reverse()
            self._reindex()
            return True
        except:
            return False
    
    def undo(self) -> bool:
        try:
            for idx, line in self._deleted_lines:
                self._project.lines.insert(idx, line)
            self._reindex()
            return True
        except:
            return False
    
    def _reindex(self):
        for i, line in enumerate(self._project.lines):
            line.index = i


class EditLineTextCommand(Command):
    """Command to edit line text"""
    
    def __init__(self, project, index: int, new_text: str):
        self._project = project
        self._index = index
        self._new_text = new_text
        self._old_text: str = ""
    
    @property
    def description(self) -> str:
        return f"Edit line {self._index + 1}"
    
    def execute(self) -> bool:
        try:
            if self._index < len(self._project.lines):
                self._old_text = self._project.lines[self._index].text
                self._project.lines[self._index].text = self._new_text
                return True
            return False
        except:
            return False
    
    def undo(self) -> bool:
        try:
            if self._index < len(self._project.lines):
                self._project.lines[self._index].text = self._old_text
                return True
            return False
        except:
            return False


class ChangeVoiceCommand(Command):
    """Command to change voice for lines"""
    
    def __init__(self, project, indices: List[int], voice_id: str, voice_name: str):
        self._project = project
        self._indices = indices
        self._voice_id = voice_id
        self._voice_name = voice_name
        self._old_voices: List[tuple] = []  # (idx, old_id, old_name)
    
    @property
    def description(self) -> str:
        return f"Change voice for {len(self._indices)} line(s)"
    
    def execute(self) -> bool:
        try:
            self._old_voices.clear()
            for idx in self._indices:
                if idx < len(self._project.lines):
                    line = self._project.lines[idx]
                    self._old_voices.append((idx, line.voice_id, line.voice_name))
                    line.voice_id = self._voice_id
                    line.voice_name = self._voice_name
            return True
        except:
            return False
    
    def undo(self) -> bool:
        try:
            for idx, old_id, old_name in self._old_voices:
                if idx < len(self._project.lines):
                    self._project.lines[idx].voice_id = old_id
                    self._project.lines[idx].voice_name = old_name
            return True
        except:
            return False


class ReorderLinesCommand(Command):
    """Command to reorder lines"""
    
    def __init__(self, project, old_order: List[int], new_order: List[int]):
        self._project = project
        self._old_order = old_order
        self._new_order = new_order
    
    @property
    def description(self) -> str:
        return "Reorder lines"
    
    def execute(self) -> bool:
        try:
            new_lines = [self._project.lines[i] for i in self._new_order]
            self._project.lines = new_lines
            self._reindex()
            return True
        except:
            return False
    
    def undo(self) -> bool:
        try:
            reverse_map = {new: old for old, new in zip(self._old_order, self._new_order)}
            current_lines = self._project.lines[:]
            for i in range(len(current_lines)):
                if i in reverse_map:
                    self._project.lines[reverse_map[i]] = current_lines[i]
            self._reindex()
            return True
        except:
            return False
    
    def _reindex(self):
        for i, line in enumerate(self._project.lines):
            line.index = i


class MergeLinesCommand(Command):
    """Command to merge multiple lines into one"""
    
    def __init__(self, project, indices: List[int]):
        self._project = project
        self._indices = sorted(indices)
        self._merged_lines: List[tuple] = []  # Original lines with positions
        self._merged_text: str = ""
    
    @property
    def description(self) -> str:
        return f"Merge {len(self._indices)} lines"
    
    def execute(self) -> bool:
        try:
            self._merged_lines.clear()
            texts = []
            
            for idx in self._indices:
                if idx < len(self._project.lines):
                    self._merged_lines.append((idx, deepcopy(self._project.lines[idx])))
                    texts.append(self._project.lines[idx].text)
            
            self._merged_text = " ".join(texts)
            
            # Keep first line with merged text
            first_idx = self._indices[0]
            self._project.lines[first_idx].text = self._merged_text
            
            # Delete other lines
            for idx in sorted(self._indices[1:], reverse=True):
                if idx < len(self._project.lines):
                    del self._project.lines[idx]
            
            self._reindex()
            return True
        except:
            return False
    
    def undo(self) -> bool:
        try:
            # Restore all merged lines
            for idx, line in self._merged_lines:
                if idx < len(self._project.lines):
                    self._project.lines[idx] = line
                else:
                    self._project.lines.insert(idx, line)
            
            self._reindex()
            return True
        except:
            return False
    
    def _reindex(self):
        for i, line in enumerate(self._project.lines):
            line.index = i


class SplitLineCommand(Command):
    """Command to split a line into two"""
    
    def __init__(self, project, index: int, split_position: int):
        self._project = project
        self._index = index
        self._split_pos = split_position
        self._original_line = None
    
    @property
    def description(self) -> str:
        return f"Split line {self._index + 1}"
    
    def execute(self) -> bool:
        try:
            if self._index >= len(self._project.lines):
                return False
            
            self._original_line = deepcopy(self._project.lines[self._index])
            
            text = self._original_line.text
            text1 = text[:self._split_pos].strip()
            text2 = text[self._split_pos:].strip()
            
            if not text2:
                return False
            
            # Update first line
            self._project.lines[self._index].text = text1
            
            # Create new line
            from core.models import TextLine
            new_line = TextLine(
                index=self._index + 1,
                text=text2,
                voice_id=self._original_line.voice_id,
                voice_name=self._original_line.voice_name,
                detected_language=self._original_line.detected_language
            )
            
            self._project.lines.insert(self._index + 1, new_line)
            self._reindex()
            return True
        except:
            return False
    
    def undo(self) -> bool:
        try:
            if self._original_line and self._index < len(self._project.lines):
                # Remove the split line
                if self._index + 1 < len(self._project.lines):
                    del self._project.lines[self._index + 1]
                
                # Restore original
                self._project.lines[self._index] = self._original_line
                self._reindex()
                return True
            return False
        except:
            return False
    
    def _reindex(self):
        for i, line in enumerate(self._project.lines):
            line.index = i


class CommandManager:
    """Manages command history for undo/redo"""
    
    def __init__(self, max_history: int = 100):
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_history = max_history
        self._on_change: Optional[Callable] = None
    
    def set_change_callback(self, callback: Callable):
        self._on_change = callback
    
    def execute(self, command: Command) -> bool:
        success = command.execute()
        if success:
            self._undo_stack.append(command)
            self._redo_stack.clear()
            
            # Limit history size
            if len(self._undo_stack) > self._max_history:
                self._undo_stack.pop(0)
            
            self._notify_change()
        return success
    
    def undo(self) -> Optional[str]:
        if not self._undo_stack:
            return None
        
        command = self._undo_stack.pop()
        if command.undo():
            self._redo_stack.append(command)
            self._notify_change()
            return command.description
        return None
    
    def redo(self) -> Optional[str]:
        if not self._redo_stack:
            return None
        
        command = self._redo_stack.pop()
        if command.execute():
            self._undo_stack.append(command)
            self._notify_change()
            return command.description
        return None
    
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0
    
    def get_undo_description(self) -> Optional[str]:
        if self._undo_stack:
            return self._undo_stack[-1].description
        return None
    
    def get_redo_description(self) -> Optional[str]:
        if self._redo_stack:
            return self._redo_stack[-1].description
        return None
    
    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify_change()
    
    def _notify_change(self):
        if self._on_change:
            self._on_change()
