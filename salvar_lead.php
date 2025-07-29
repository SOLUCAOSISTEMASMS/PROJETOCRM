<?php
$host = 'localhost';
$db   = 'seu_banco';
$user = 'seu_usuario';
$pass = 'sua_senha';

$conn = new mysqli($host, $user, $pass, $db);
if ($conn->connect_error) die("Erro de conexão");

$stmt = $conn->prepare("INSERT INTO leads (nome, email, telefone, empresa, cargo, origem, status, interesses, observacoes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
$stmt->bind_param("sssssssss", $_POST['nome'], $_POST['email'], $_POST['telefone'], $_POST['empresa'], $_POST['cargo'], $_POST['origem'], $_POST['status'], $_POST['interesses'], $_POST['observacoes']);
$stmt->execute();
$stmt->close();
$conn->close();

echo "Lead salvo com sucesso!";
?>