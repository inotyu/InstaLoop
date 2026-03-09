import magic
import uuid
import io
import os
from PIL import Image, ImageOps
from typing import Tuple, Optional
from flask import current_app
from utils.audit import log_security_event

# Tipos MIME permitidos
ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/png', 
    'image/webp'
}

# Extensões correspondentes
MIME_TO_EXTENSION = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp'
}

# Tamanhos máximos
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_DIMENSION = 4096  # pixels
MIN_IMAGE_DIMENSION = 100   # pixels

class ImageProcessor:
    """
    Processador de imagens com segurança zero-trust.
    """
    
    @staticmethod
    def process_uploaded_image(file_bytes: bytes, filename: str = None) -> Tuple[bytes, str, dict]:
        """
        Processa imagem de forma segura: validação, re-renderização e sanitização.
        
        Returns:
            Tuple[bytes, str, dict]: (imagem_processada, nome_arquivo, metadados)
        """
        metadata = {
            'original_filename': filename,
            'original_size': len(file_bytes),
            'processed': False,
            'errors': []
        }
        
        try:
            # 1. Validação básica de tamanho
            if len(file_bytes) > MAX_FILE_SIZE:
                raise ValueError(f"Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB")
            
            if len(file_bytes) == 0:
                raise ValueError("Arquivo vazio")
            
            # 2. Validação de magic bytes (não confiar em Content-Type)
            mime_type = magic.from_buffer(file_bytes[:2048], mime=True)
            metadata['detected_mime'] = mime_type
            
            if mime_type not in ALLOWED_MIME_TYPES:
                raise ValueError(f"Tipo de arquivo não permitido: {mime_type}")
            
            # 3. Validação e abertura da imagem
            try:
                # Primeiro, verificar se é uma imagem válida
                img = Image.open(io.BytesIO(file_bytes))
                img.verify()  # Detecta corrupção
                
                # Reabrir após verify() (verify() fecha a imagem)
                img = Image.open(io.BytesIO(file_bytes))
                
                metadata['original_format'] = img.format
                metadata['original_size'] = img.size
                metadata['original_mode'] = img.mode
                
            except Exception as e:
                raise ValueError(f"Arquivo de imagem inválido ou corrompido: {str(e)}")
            
            # 4. Validações de dimensões
            width, height = img.size
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                raise ValueError(f"Dimensões muito grandes. Máximo: {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}")
            
            if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                raise ValueError(f"Dimensões muito pequenas. Mínimo: {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}")
            
            # 5. Normalização e re-renderização (zero-trust)
            processed_img = ImageProcessor._normalize_image(img, mime_type)
            
            # 6. Remoção de metadados EXIF e outros dados
            processed_img = ImageProcessor._strip_metadata(processed_img)
            
            # 7. Otimização e compressão
            output_buffer = io.BytesIO()
            output_format = ImageProcessor._get_output_format(mime_type)
            
            save_kwargs = ImageProcessor._get_save_kwargs(output_format)
            processed_img.save(output_buffer, format=output_format, **save_kwargs)
            
            processed_bytes = output_buffer.getvalue()
            
            # 8. Validação final
            if len(processed_bytes) > MAX_FILE_SIZE:
                raise ValueError("Imagem processada muito grande")
            
            # 9. Gerar nome seguro (UUID)
            extension = MIME_TO_EXTENSION[mime_type]
            safe_filename = f"{uuid.uuid4()}{extension}"
            
            metadata.update({
                'processed': True,
                'final_size': len(processed_bytes),
                'final_dimensions': processed_img.size,
                'final_format': output_format,
                'compression_ratio': len(processed_bytes) / len(file_bytes),
                'safe_filename': safe_filename
            })
            
            return processed_bytes, safe_filename, metadata
            
        except Exception as e:
            metadata['errors'].append(str(e))
            log_security_event(
                'file_upload_blocked',
                details={
                    'filename': filename,
                    'error': str(e),
                    'file_size': len(file_bytes),
                    'metadata': metadata
                }
            )
            raise ValueError(str(e))
    
    @staticmethod
    def _normalize_image(img: Image.Image, mime_type: str) -> Image.Image:
        """
        Normaliza imagem para formato seguro.
        """
        # Converter para RGB se necessário
        if img.mode not in ('RGB', 'RGBA'):
            if img.mode == 'P':
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
        
        # Auto-orientar baseado em EXIF (mas depois vamos remover EXIF)
        img = ImageOps.exif_transpose(img)
        
        # Para transparência em JPEG, converter para RGB com fundo branco
        if mime_type == 'image/jpeg' and img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])  # Alpha channel
            img = background
        
        return img
    
    @staticmethod
    def _strip_metadata(img: Image.Image) -> Image.Image:
        """
        Remove todos os metadados da imagem.
        """
        # Criar nova imagem sem metadados
        if img.mode == 'RGBA':
            clean_img = Image.new('RGBA', img.size, (255, 255, 255, 0))
        else:
            clean_img = Image.new('RGB', img.size, (255, 255, 255))
        
        clean_img.paste(img)
        
        # Remover todos os atributos de metadados
        if hasattr(clean_img, '_getexif'):
            exif = clean_img._getexif()
            if exif is not None:
                exif.clear()
        
        # Limpar outros metadados
        for attr in ['info', 'tag', 'ap']:
            if hasattr(clean_img, attr):
                setattr(clean_img, attr, {})
        
        return clean_img
    
    @staticmethod
    def _get_output_format(mime_type: str) -> str:
        """
        Determina formato de saída baseado no MIME type.
        """
        format_map = {
            'image/jpeg': 'JPEG',
            'image/png': 'PNG',
            'image/webp': 'WEBP'
        }
        return format_map.get(mime_type, 'JPEG')
    
    @staticmethod
    def _get_save_kwargs(format: str) -> dict:
        """
        Retorna parâmetros de salvamento para cada formato.
        """
        if format == 'JPEG':
            return {
                'quality': 85,
                'optimize': True,
                'progressive': True
            }
        elif format == 'PNG':
            return {
                'optimize': True,
                'compress_level': 6
            }
        elif format == 'WEBP':
            return {
                'quality': 85,
                'optimize': True,
                'method': 4
            }
        else:
            return {'optimize': True}
    
    @staticmethod
    def validate_image_content(file_bytes: bytes) -> dict:
        """
        Validação adicional do conteúdo da imagem.
        """
        validation_result = {
            'is_valid': True,
            'issues': [],
            'warnings': []
        }
        
        try:
            img = Image.open(io.BytesIO(file_bytes))
            
            # Verificar se parece ser uma imagem real (não ruído aleatório)
            pixels = list(img.getdata())
            unique_colors = len(set(pixels))
            
            # Se tiver muito poucas cores, pode ser suspeito
            if unique_colors < 10:
                validation_result['warnings'].append('Imagem com pouquíssimas cores')
            
            # Verificar proporções extremas
            width, height = img.size
            ratio = max(width, height) / min(width, height)
            
            if ratio > 10:
                validation_result['warnings'].append('Proporção extremamente alongada')
            
            # Análise estatística básica
            if len(pixels) > 1000:
                sample_pixels = pixels[:1000]
                
                # Calcular "entropia" visual simples
                color_variance = sum(
                    sum((c1 - c2) ** 2 for c1, c2 in zip(pixel[:3], sample_pixels[0][:3]))
                    for pixel in sample_pixels[1:]
                ) / len(sample_pixels)
                
                if color_variance < 100:
                    validation_result['warnings'].append('Baixa variação de cores')
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['issues'].append(f'Erro na análise: {str(e)}')
        
        return validation_result
    
    @staticmethod
    def create_thumbnail(file_bytes: bytes, max_size: int = 200) -> bytes:
        """
        Cria thumbnail seguro da imagem.
        """
        try:
            img = Image.open(io.BytesIO(file_bytes))
            
            # Converter para RGB se necessário
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Calcular tamanho mantendo proporção
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Salvar thumbnail
            output_buffer = io.BytesIO()
            img.save(output_buffer, format='JPEG', quality=85, optimize=True)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            raise ValueError(f"Erro ao criar thumbnail: {str(e)}")
    
    @staticmethod
    def save_image_to_disk(file_bytes: bytes, filename: str, upload_dir: str = None) -> str:
        """
        Salva imagem processada em disco de forma segura.
        """
        try:
            if upload_dir is None:
                upload_dir = current_app.config.get('UPLOAD_DIR', 'static/uploads')
            
            # Criar diretório se não existir
            os.makedirs(upload_dir, exist_ok=True)
            
            # Caminho completo do arquivo
            file_path = os.path.join(upload_dir, filename)
            
            # Verificar se arquivo já existe (UUID deveria evitar, mas por segurança)
            if os.path.exists(file_path):
                raise ValueError("Arquivo já existe")
            
            # Salvar arquivo
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            
            # Definir permissões seguras
            os.chmod(file_path, 0o644)  # rw-r--r--
            
            return file_path
            
        except Exception as e:
            raise ValueError(f"Erro ao salvar imagem: {str(e)}")
    
    @staticmethod
    def delete_image_from_disk(filename: str, upload_dir: str = None) -> bool:
        """
        Remove imagem do disco de forma segura.
        """
        try:
            if upload_dir is None:
                upload_dir = current_app.config.get('UPLOAD_DIR', 'static/uploads')
            
            file_path = os.path.join(upload_dir, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            
            return False
            
        except Exception:
            return False

# Funções de conveniência
def process_upload(file_storage, upload_dir: str = None) -> Tuple[str, dict]:
    """
    Processa upload de arquivo completo.
    
    Returns:
        Tuple[str, dict]: (nome_arquivo, metadados)
    """
    if not file_storage or not hasattr(file_storage, 'read'):
        raise ValueError("Arquivo inválido")
    
    # Ler bytes do arquivo
    file_bytes = file_storage.read()
    original_filename = getattr(file_storage, 'filename', 'unknown')
    
    # Processar imagem
    processed_bytes, safe_filename, metadata = ImageProcessor.process_uploaded_image(
        file_bytes, original_filename
    )
    
    # Salvar em disco
    if upload_dir is None:
        upload_dir = current_app.config.get('UPLOAD_DIR', 'static/uploads')
    
    file_path = ImageProcessor.save_image_to_disk(processed_bytes, safe_filename, upload_dir)
    
    # Adicionar caminho aos metadados
    metadata['file_path'] = file_path
    metadata['relative_url'] = f"/{file_path}"
    
    return safe_filename, metadata

def validate_image_file(file_storage) -> Tuple[bool, list]:
    """
    Valida arquivo de upload antes do processamento completo.
    """
    errors = []
    
    if not file_storage:
        errors.append("Nenhum arquivo fornecido")
        return False, errors
    
    if not hasattr(file_storage, 'read'):
        errors.append("Arquivo inválido")
        return False, errors
    
    # Verificar tamanho
    file_storage.seek(0, 2)  # Ir para o fim
    file_size = file_storage.tell()
    file_storage.seek(0)     # Voltar ao início
    
    if file_size > MAX_FILE_SIZE:
        errors.append(f"Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB")
    
    if file_size == 0:
        errors.append("Arquivo vazio")
    
    # Verificar MIME type
    try:
        file_bytes = file_storage.read(2048)
        file_storage.seek(0)
        
        mime_type = magic.from_buffer(file_bytes, mime=True)
        if mime_type not in ALLOWED_MIME_TYPES:
            errors.append(f"Tipo de arquivo não permitido: {mime_type}")
    
    except Exception as e:
        errors.append(f"Erro ao ler arquivo: {str(e)}")
    
    return len(errors) == 0, errors
